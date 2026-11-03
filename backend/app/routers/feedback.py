import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_owned_interview
from ..models.answer import Answer
from ..models.feedback import Feedback
from ..models.interview import Interview
from ..models.interview_question import InterviewQuestion
from ..schemas.feedback import FeedbackReport
from ..services.gemini_feedback import FeedbackGenerationError, generate_feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interviews", tags=["Feedback"])


def _saved_report(db: Session, interview_id: int) -> FeedbackReport | None:
    saved = db.scalar(select(Feedback).where(Feedback.interview_id == interview_id))
    if saved is None:
        return None
    return FeedbackReport.model_validate(saved, from_attributes=True)


@router.post(
    "/{interview_id}/feedback",
    response_model=FeedbackReport,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(
    response: Response,
    interview: Annotated[Interview, Depends(get_owned_interview)],
    db: Session = Depends(get_db),
):
    """Create the interview's feedback report, or return the one already saved."""
    # 1. Already have a report? Return it and do not call Gemini again.
    existing = _saved_report(db, interview.id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    # 2. Every question must have a saved answer.
    rows = db.execute(
        select(InterviewQuestion.question_text, Answer.answer_text)
        .join(Answer, Answer.interview_question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview.id)
        .order_by(InterviewQuestion.question_order)
    ).all()
    total_questions = db.scalar(
        select(func.count(InterviewQuestion.id)).where(
            InterviewQuestion.interview_id == interview.id
        )
    )
    if not total_questions or len(rows) < total_questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback is only available after all questions are answered.",
        )

    qa_pairs = [{"question": question, "answer": answer} for question, answer in rows]

    # 3. Ask Gemini. A failure or invalid data gives a controlled 502 and saves nothing.
    try:
        report = FeedbackReport.model_validate(generate_feedback(qa_pairs))
    except (FeedbackGenerationError, ValidationError) as error:
        logger.warning(
            "Feedback generation failed for interview %s: %s",
            interview.id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate feedback right now. Please try again.",
        )

    # 4. Save the report. There can be only one report per interview.
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
        # Otherwise the generated report broke a database rule (for example a score range).
        logger.warning("Generated feedback rejected by the database for interview %s", interview.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate feedback right now. Please try again.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the feedback.",
        )

    return report
