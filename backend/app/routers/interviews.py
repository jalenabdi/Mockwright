"""Interview endpoints: start, history, detail, current turn and answers."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..dependencies import CurrentUser, DbSession, OwnedInterview
from ..models import Answer, Feedback, FollowUp, Interview, InterviewQuestion, Resume
from ..schemas.feedback import FeedbackReport
from ..schemas.interview import (
    CurrentQuestionResponse,
    FollowUpOut,
    InterviewDetail,
    InterviewSummary,
    QuestionOut,
    QuestionWithAnswer,
    StartInterviewRequest,
)
from ..schemas.typed_answer import SubmitAnswerResponse, TypedAnswerInput, TypedAnswerReturn
from ..services import interview_service
from ..services.exceptions import (
    AnswerAlreadyExistsError,
    BlankAnswerError,
    InterviewAlreadyCompletedError,
    InterviewNotFoundError,
    InterviewServiceError,
    QuestionNotInInterviewError,
    QuestionOutOfOrderError,
)
from ..services.recording_store import RecordingStore, get_recording_store
from ..services.question_generator import (
    TOTAL_QUESTIONS,
    InterviewContext,
    QuestionGenerator,
    get_question_generator,
)

router = APIRouter(prefix="/interviews", tags=["Interviews"])

Generator = Annotated[QuestionGenerator, Depends(get_question_generator)]
Store = Annotated[RecordingStore, Depends(get_recording_store)]

# Each service error maps to one HTTP status and one user-facing message.
_ERRORS: dict[type[InterviewServiceError], tuple[int, str]] = {
    InterviewNotFoundError: (status.HTTP_404_NOT_FOUND, "Interview not found."),
    InterviewAlreadyCompletedError: (status.HTTP_409_CONFLICT, "This interview has already been completed."),
    QuestionNotInInterviewError: (status.HTTP_400_BAD_REQUEST, "The question does not belong to this interview."),
    QuestionOutOfOrderError: (
        status.HTTP_409_CONFLICT,
        "This question is not the current question for the interview.",
    ),
    AnswerAlreadyExistsError: (status.HTTP_409_CONFLICT, "An answer for this question has already been submitted."),
    BlankAnswerError: (status.HTTP_422_UNPROCESSABLE_CONTENT, "Answer text cannot be empty."),
}


def _follow_up_out(follow_up: FollowUp) -> FollowUpOut:
    return FollowUpOut(
        id=follow_up.id,
        question_id=follow_up.interview_question_id,
        position=follow_up.position,
        question_text=follow_up.question_text,
        answer_text=follow_up.answer_text,
    )


def _load_detail(db: Session, interview_id: int) -> InterviewDetail:
    interview = db.scalar(
        select(Interview)
        .where(Interview.id == interview_id)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
            selectinload(Interview.questions).selectinload(InterviewQuestion.recording),
            selectinload(Interview.questions).selectinload(InterviewQuestion.follow_ups),
            selectinload(Interview.feedback),
        )
        .execution_options(populate_existing=True)
    )
    assert interview is not None
    questions = [
        QuestionWithAnswer(
            id=q.id,
            question_order=q.question_order,
            question_text=q.question_text,
            answer_text=q.answer.answer_text if q.answer else None,
            has_recording=q.recording is not None,
            follow_ups=[_follow_up_out(f) for f in q.follow_ups],
        )
        for q in interview.questions
    ]
    current = next(
        (q for q in interview.questions if q.question_order == interview.current_question_position),
        None,
    )
    open_follow_up = next(
        (f for f in (current.follow_ups if current else []) if f.answer_text is None), None
    )
    feedback = (
        FeedbackReport.model_validate(interview.feedback) if interview.feedback else None
    )
    return InterviewDetail(
        id=interview.id,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        job_description=interview.job_description,
        used_resume=bool(interview.resume_text),
        status=interview.status,
        current_question_position=interview.current_question_position,
        answered_count=sum(1 for q in questions if q.answer_text is not None),
        total_questions=TOTAL_QUESTIONS,
        created_at=interview.created_at,
        total_score=feedback.total_score if feedback else None,
        current_question=QuestionOut.model_validate(current) if current else None,
        current_follow_up=_follow_up_out(open_follow_up) if open_follow_up else None,
        questions=questions,
        feedback=feedback,
    )


@router.post("/start", response_model=InterviewDetail, status_code=status.HTTP_201_CREATED)
def start_interview(
    payload: StartInterviewRequest,
    current_user: CurrentUser,
    db: DbSession,
    generator: Generator,
) -> InterviewDetail:
    """Start an interview. Question 1 is written for the role, level, job description and resume."""
    resume_text = None
    if payload.use_resume:
        resume_text = db.scalar(select(Resume.text).where(Resume.user_id == current_user.id))
        if resume_text is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload your resume first, or start without it.",
            )
    interview = interview_service.start_interview(
        db,
        user_id=current_user.id,
        context=InterviewContext(
            target_role=payload.target_role,
            experience_level=payload.experience_level.value,
            job_description=payload.job_description or None,
            resume=resume_text,
        ),
        generator=generator,
    )
    return _load_detail(db, interview.id)


@router.get("", response_model=list[InterviewSummary])
def list_interviews(current_user: CurrentUser, db: DbSession) -> list[InterviewSummary]:
    """The signed-in user's interviews, newest first."""
    answered = (
        select(InterviewQuestion.interview_id, func.count(Answer.id).label("answered"))
        .join(Answer, Answer.interview_question_id == InterviewQuestion.id)
        .group_by(InterviewQuestion.interview_id)
        .subquery()
    )
    rows = db.execute(
        select(Interview, func.coalesce(answered.c.answered, 0), Feedback.total_score)
        .outerjoin(answered, answered.c.interview_id == Interview.id)
        .outerjoin(Feedback, Feedback.interview_id == Interview.id)
        .where(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc(), Interview.id.desc())
    ).all()
    return [
        InterviewSummary(
            id=interview.id,
            target_role=interview.target_role,
            experience_level=interview.experience_level,
            status=interview.status,
            answered_count=count,
            total_questions=TOTAL_QUESTIONS,
            created_at=interview.created_at,
            total_score=score,
        )
        for interview, count, score in rows
    ]


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(interview: OwnedInterview, db: DbSession) -> InterviewDetail:
    """Status, progress, and every question asked so far with its answer."""
    return _load_detail(db, interview.id)


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(interview: OwnedInterview, db: DbSession, store: Store) -> Response:
    """Delete the interview with its questions, answers, feedback and videos."""
    user_id, interview_id = interview.user_id, interview.id
    db.delete(interview)
    db.commit()
    store.delete_interview(user_id, interview_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{interview_id}/current-question", response_model=CurrentQuestionResponse)
def get_current_question(
    interview: OwnedInterview, db: DbSession, generator: Generator
) -> CurrentQuestionResponse:
    """What to answer next: a question, or a follow-up on it. Decides it first if needed."""
    turn = interview_service.current_turn(db, interview, generator)
    if turn is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview has already been completed.",
        )
    return CurrentQuestionResponse(
        interview_id=interview.id,
        current_position=interview.current_question_position,
        total_questions=TOTAL_QUESTIONS,
        status=interview.status,
        question=QuestionOut.model_validate(turn.question),
        follow_up=_follow_up_out(turn.follow_up) if turn.follow_up else None,
    )


@router.post(
    "/{interview_id}/answers",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_answer(
    payload: TypedAnswerInput,
    interview: OwnedInterview,
    db: DbSession,
    generator: Generator,
) -> SubmitAnswerResponse:
    """Save an answer (typed or a voice transcript) and get what comes next.

    That is a follow-up on the same question, the next question, or neither
    once the interview is completed.
    """
    try:
        if payload.follow_up_id is None:
            answer = interview_service.save_answer(
                db, interview.id, payload.question_id, payload.answer_text
            )
            saved = TypedAnswerReturn(
                id=answer.id, question_id=answer.interview_question_id, answer_text=answer.answer_text
            )
        else:
            follow_up = interview_service.save_follow_up_answer(
                db, interview.id, payload.question_id, payload.follow_up_id, payload.answer_text
            )
            saved = TypedAnswerReturn(
                id=follow_up.id,
                question_id=follow_up.interview_question_id,
                answer_text=follow_up.answer_text or "",
            )
    except InterviewServiceError as error:
        code, detail = _ERRORS.get(type(error), (status.HTTP_400_BAD_REQUEST, "Could not save the answer."))
        raise HTTPException(status_code=code, detail=detail)

    turn = interview_service.current_turn(db, interview, generator)
    return SubmitAnswerResponse(
        answer=saved,
        status=interview.status,
        answered_count=interview_service.answered_count(db, interview.id),
        total_questions=TOTAL_QUESTIONS,
        follow_up=_follow_up_out(turn.follow_up) if turn and turn.follow_up else None,
        next_question=(
            QuestionOut.model_validate(turn.question) if turn and turn.follow_up is None else None
        ),
    )
