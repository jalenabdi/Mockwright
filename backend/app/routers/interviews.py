"""Interview endpoints: start, history, detail, current question and answers."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..dependencies import CurrentUser, DbSession, OwnedInterview
from ..models import Answer, Feedback, Interview, InterviewQuestion
from ..schemas.feedback import FeedbackReport
from ..schemas.interview import (
    CurrentQuestionResponse,
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
from ..services.question_generator import (
    TOTAL_QUESTIONS,
    QuestionGenerator,
    get_question_generator,
)

router = APIRouter(prefix="/interviews", tags=["Interviews"])

Generator = Annotated[QuestionGenerator, Depends(get_question_generator)]

_ERROR_STATUS: dict[type[InterviewServiceError], int] = {
    InterviewNotFoundError: status.HTTP_404_NOT_FOUND,
    InterviewAlreadyCompletedError: status.HTTP_409_CONFLICT,
    QuestionNotInInterviewError: status.HTTP_400_BAD_REQUEST,
    QuestionOutOfOrderError: status.HTTP_409_CONFLICT,
    AnswerAlreadyExistsError: status.HTTP_409_CONFLICT,
    BlankAnswerError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

_ERROR_DETAIL: dict[type[InterviewServiceError], str] = {
    InterviewNotFoundError: "Interview not found.",
    InterviewAlreadyCompletedError: "This interview has already been completed.",
    QuestionNotInInterviewError: "The question does not belong to this interview.",
    QuestionOutOfOrderError: "This question is not the current question for the interview.",
    AnswerAlreadyExistsError: "An answer for this question has already been submitted.",
    BlankAnswerError: "Answer text cannot be empty.",
}


def _load_detail(db: Session, interview_id: int) -> InterviewDetail:
    interview = db.scalar(
        select(Interview)
        .where(Interview.id == interview_id)
        .options(
            selectinload(Interview.questions).selectinload(InterviewQuestion.answer),
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
        )
        for q in interview.questions
    ]
    current = next(
        (q for q in interview.questions if q.question_order == interview.current_question_position),
        None,
    )
    feedback = (
        FeedbackReport.model_validate(interview.feedback) if interview.feedback else None
    )
    return InterviewDetail(
        id=interview.id,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        job_description=interview.job_description,
        status=interview.status,
        current_question_position=interview.current_question_position,
        answered_count=sum(1 for q in questions if q.answer_text is not None),
        total_questions=TOTAL_QUESTIONS,
        created_at=interview.created_at,
        total_score=feedback.total_score if feedback else None,
        current_question=QuestionOut.model_validate(current) if current else None,
        questions=questions,
        feedback=feedback,
    )


@router.post("/start", response_model=InterviewDetail, status_code=status.HTTP_201_CREATED)
def start_interview(
    settings: StartInterviewRequest,
    current_user: CurrentUser,
    db: DbSession,
    generator: Generator,
) -> InterviewDetail:
    """Start an interview. Question 1 is written for the role, level and job description."""
    interview = interview_service.start_interview(
        db,
        user_id=current_user.id,
        target_role=settings.target_role,
        experience_level=settings.experience_level.value,
        job_description=settings.job_description,
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


@router.get("/{interview_id}/current-question", response_model=CurrentQuestionResponse)
def get_current_question(
    interview: OwnedInterview, db: DbSession, generator: Generator
) -> CurrentQuestionResponse:
    """The question to answer next. Writes it first if it doesn't exist yet."""
    question = interview_service.ensure_current_question(db, interview, generator)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview has already been completed.",
        )
    return CurrentQuestionResponse(
        interview_id=interview.id,
        current_position=interview.current_question_position,
        total_questions=TOTAL_QUESTIONS,
        status=interview.status,
        question=QuestionOut.model_validate(question),
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
    """Save an answer (typed or a voice transcript) and get the next question."""
    try:
        result = interview_service.save_answer(
            db, interview.id, payload.question_id, payload.answer_text
        )
    except InterviewServiceError as error:
        raise HTTPException(
            status_code=_ERROR_STATUS.get(type(error), status.HTTP_400_BAD_REQUEST),
            detail=_ERROR_DETAIL.get(type(error), "Could not save the answer."),
        )

    db.refresh(interview)
    next_question = interview_service.ensure_current_question(db, interview, generator)
    return SubmitAnswerResponse(
        answer=TypedAnswerReturn(
            id=result.answer.id,
            question_id=result.answer.interview_question_id,
            answer_text=result.answer.answer_text,
        ),
        status=result.status,
        answered_count=result.answered_count,
        total_questions=result.total_questions,
        next_question=QuestionOut.model_validate(next_question) if next_question else None,
    )
