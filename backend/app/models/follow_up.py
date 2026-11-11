from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .interview_question import InterviewQuestion


class FollowUp(Base):
    """A short follow-up the interviewer asked about a main question's answer.

    position counts follow-ups within their question (1, 2). answer_text is
    empty until the candidate answers it.
    """

    __tablename__ = "follow_ups"
    __table_args__ = (
        UniqueConstraint(
            "interview_question_id", "position", name="uq_follow_ups_interview_question_id_position"
        ),
        CheckConstraint("position >= 1", name="ck_follow_ups_position_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_question_id: Mapped[int] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question: Mapped[InterviewQuestion] = relationship(back_populates="follow_ups")
