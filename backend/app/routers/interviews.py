import logging
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_owned_interview
from ..models.answer import Answer
from ..models.interview import Interview
from ..models.interview_question import InterviewQuestion
from ..models.user import User
from ..schemas.interview import (
    InterviewDetail,
    InterviewListItem,
    InterviewQuestionDetail,
)
from ..schemas.typed_answer import TypedAnswerInput, TypedAnswerReturn
from ..services.exceptions import (
    AnswerAlreadyExistsError,
    BlankAnswerError,
    InterviewAlreadyCompletedError,
    InterviewNotFoundError,
    InterviewServiceError,
    QuestionNotInInterviewError,
    QuestionOutOfOrderError,
)
from ..services.interview_service import save_answer

router = APIRouter(prefix="/interviews", tags=["Interviews"])
logger = logging.getLogger(__name__)


class InterviewProgress(TypedDict):
    answered_count: int
    total_questions: int
    current_question_number: int | None
    progress_percent: int


def _interview_progress(
    interview: Interview,
    answered_count: int | None,
    total_questions: int | None,
) -> InterviewProgress:
    answered_count = answered_count or 0
    total_questions = total_questions or 0
    is_complete = (
        interview.status == "completed"
        or interview.current_question_position > total_questions
    )
    return {
        "answered_count": answered_count,
        "total_questions": total_questions,
        "current_question_number": (
            None
            if is_complete
            else interview.current_question_position
        ),
        "progress_percent": (
            round(answered_count * 100 / total_questions) if total_questions else 0
        ),
    }


@router.get("", response_model=list[InterviewListItem])
def list_interviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the signed-in user's interviews, newest first, with progress."""
    rows = db.execute(
        select(
            Interview,
            func.count(Answer.id),
            func.count(InterviewQuestion.id),
        )
        .outerjoin(
            InterviewQuestion,
            InterviewQuestion.interview_id == Interview.id,
        )
        .outerjoin(
            Answer,
            Answer.interview_question_id == InterviewQuestion.id,
        )
        .where(Interview.user_id == current_user.id)
        .group_by(Interview.id)
        .order_by(Interview.created_at.desc(), Interview.id.desc())
    ).all()

    return [
        InterviewListItem(
            id=interview.id,
            target_role=interview.target_role,
            experience_level=interview.experience_level,
            status=interview.status,
            created_at=interview.created_at,
            **_interview_progress(interview, answered_count, total_questions),
        )
        for interview, answered_count, total_questions in rows
    ]


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(
    interview: Interview = Depends(get_owned_interview),
    db: Session = Depends(get_db),
):
    """Return one owned interview with its ordered questions and saved answers."""
    question_rows = db.execute(
        select(InterviewQuestion, Answer.answer_text)
        .outerjoin(
            Answer,
            Answer.interview_question_id == InterviewQuestion.id,
        )
        .where(InterviewQuestion.interview_id == interview.id)
        .order_by(InterviewQuestion.question_order)
    ).all()
    answered_count = sum(answer_text is not None for _, answer_text in question_rows)
    total_questions = len(question_rows)

    return InterviewDetail(
        id=interview.id,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        status=interview.status,
        created_at=interview.created_at,
        job_description=interview.job_description,
        updated_at=interview.updated_at,
        questions=[
            InterviewQuestionDetail(
                id=question.id,
                question_order=question.question_order,
                question_text=question.question_text,
                answer_text=answer_text,
            )
            for question, answer_text in question_rows
        ],
        **_interview_progress(interview, answered_count, total_questions),
    )


@router.get("/{interview_id}/current-question")
def get_current_question(
    interview: Interview = Depends(get_owned_interview),
    db: Session = Depends(get_db),
):
    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview has already been completed.",
        )

    current_question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.interview_id == interview.id,
            InterviewQuestion.question_order == interview.current_question_position,
        )
        .first()
    )

    if not current_question:
        logger.error(
            "Interview %s has no question at position %s",
            interview.id,
            interview.current_question_position,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No current question is available for this interview.",
        )

    return {
        "interview_id": interview.id,
        "current_position": interview.current_question_position,
        "status": interview.status,
        "question": {
            "id": current_question.id,
            "text": current_question.question_text,
            "question_order": current_question.question_order,
        },
    }


@router.post("/{interview_id}/answers", status_code=status.HTTP_201_CREATED)
def submit_answer(
    payload: TypedAnswerInput,
    interview: Interview = Depends(get_owned_interview),
    db: Session = Depends(get_db),
):
    """Submit a typed answer for the current question in an interview."""
    try:
        result = save_answer(
            db,
            interview.id,
            payload.question_id,
            payload.answer_text,
        )
    except InterviewAlreadyCompletedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview has already been completed.",
        ) from None
    except AnswerAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An answer for this question has already been submitted.",
        ) from None
    except QuestionOutOfOrderError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is not the current question for the interview.",
        ) from None
    except QuestionNotInInterviewError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The question does not belong to this interview.",
        ) from None
    except BlankAnswerError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Answer text cannot be empty or whitespace.",
        ) from None
    except InterviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        ) from None
    except InterviewServiceError:
        logger.exception("Could not save answer for interview %s", interview.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the answer. Please try again.",
        ) from None
    except SQLAlchemyError:
        logger.exception("Database error saving answer for interview %s", interview.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the answer. Please try again.",
        ) from None

    return TypedAnswerReturn(
        id=result.answer.id,
        question_id=result.answer.interview_question_id,
        answer_text=result.answer.answer_text,
    )