import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..dependencies import DbSession, OwnedInterview
from ..models import STATUS_COMPLETED, Feedback
from ..schemas.feedback import FeedbackReport
from ..services.gemini_feedback import (
    FeedbackGenerationError,
    FeedbackGenerator,
    FeedbackUnavailableError,
    get_feedback_generator,
)
from ..services.interview_service import context_for, conversation_so_far
from ..services.question_generator import TOTAL_QUESTIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interviews", tags=["Feedback"])

GENERATION_FAILED_DETAIL = "Could not generate feedback right now. Please try again."


def _saved_report(db: Session, interview_id: int) -> FeedbackReport | None:
    saved = db.scalar(select(Feedback).where(Feedback.interview_id == interview_id))
    if saved is None:
        return None
    return FeedbackReport.model_validate(saved)


@router.post(
    "/{interview_id}/feedback",
    response_model=FeedbackReport,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(
    response: Response,
    interview: OwnedInterview,
    db: DbSession,
    generator: Annotated[FeedbackGenerator, Depends(get_feedback_generator)],
) -> FeedbackReport:
    """Create the interview's feedback report, or return the one already saved."""
    existing = _saved_report(db, interview.id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    turns = conversation_so_far(db, interview.id)
    if interview.status != STATUS_COMPLETED or len(turns) < TOTAL_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback is only available after all questions are answered.",
        )

    try:
        report = generator.generate(context_for(interview), turns)
    except FeedbackUnavailableError:
        logger.warning("Feedback requested but GEMINI_API_KEY is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback is not available because the AI service is not configured.",
        )
    except FeedbackGenerationError as error:
        logger.warning("Feedback generation failed for interview %s: %s", interview.id, error)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=GENERATION_FAILED_DETAIL)

    try:
        db.add(Feedback(interview_id=interview.id, **report.model_dump(mode="json")))
        db.commit()
    except IntegrityError:
        db.rollback()
        # A simultaneous request may have saved a report first: return that one.
        existing = _saved_report(db, interview.id)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing
        logger.warning("Generated feedback rejected by the database for interview %s", interview.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=GENERATION_FAILED_DETAIL)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the feedback.",
        )

    return report


@router.get("/{interview_id}/feedback", response_model=FeedbackReport)
def get_feedback(interview: OwnedInterview, db: DbSession) -> FeedbackReport:
    """Return the saved feedback report for the user's interview."""
    report = _saved_report(db, interview.id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback was not found for this interview.",
        )
    return report
