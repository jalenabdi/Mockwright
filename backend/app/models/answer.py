from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .interview_question import InterviewQuestion


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("interview_question_id", name="uq_answers_interview_question_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_question_id: Mapped[int] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE")
    )
    answer_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question: Mapped[InterviewQuestion] = relationship(back_populates="answer")
