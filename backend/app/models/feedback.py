from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, PortableJSON

if TYPE_CHECKING:
    from .interview import Interview


class Feedback(Base):
    """The single saved AI feedback report for a completed interview."""

    __tablename__ = "feedbacks"
    __table_args__ = (
        UniqueConstraint("interview_id", name="uq_feedbacks_interview_id"),
        CheckConstraint("relevance_score BETWEEN 0 AND 20", name="ck_feedbacks_relevance_score_range"),
        CheckConstraint("star_structure_score BETWEEN 0 AND 20", name="ck_feedbacks_star_structure_score_range"),
        CheckConstraint("specificity_score BETWEEN 0 AND 20", name="ck_feedbacks_specificity_score_range"),
        CheckConstraint(
            "individual_contribution_score BETWEEN 0 AND 20",
            name="ck_feedbacks_individual_contribution_score_range",
        ),
        CheckConstraint("communication_score BETWEEN 0 AND 20", name="ck_feedbacks_communication_score_range"),
        CheckConstraint("total_score BETWEEN 0 AND 100", name="ck_feedbacks_total_score_range"),
        CheckConstraint(
            "total_score = relevance_score + star_structure_score + specificity_score"
            " + individual_contribution_score + communication_score",
            name="ck_feedbacks_total_score_sum",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"))

    relevance_score: Mapped[int]
    star_structure_score: Mapped[int]
    specificity_score: Mapped[int]
    individual_contribution_score: Mapped[int]
    communication_score: Mapped[int]
    total_score: Mapped[int]

    strengths: Mapped[list[str]] = mapped_column(PortableJSON)
    improvements: Mapped[list[str]] = mapped_column(PortableJSON)
    next_step: Mapped[str] = mapped_column(Text)
    # [{"question_number", "score", "comment"}, ...]; [] for reports saved before grades existed.
    question_grades: Mapped[list[dict]] = mapped_column(
        PortableJSON, default=list, server_default=text("'[]'")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    interview: Mapped[Interview] = relationship(back_populates="feedback")
