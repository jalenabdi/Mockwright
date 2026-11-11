from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .answer import Answer
    from .interview import Interview


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        UniqueConstraint(
            "interview_id",
            "question_order",
            name="uq_interview_questions_interview_id_question_order",
        ),
        CheckConstraint(
            "question_order >= 1",
            name="ck_interview_questions_question_order_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    question_order: Mapped[int]
    question_text: Mapped[str] = mapped_column(Text)

    interview: Mapped[Interview] = relationship(back_populates="questions")
    answer: Mapped[Answer | None] = relationship(
        back_populates="question", cascade="all, delete-orphan", passive_deletes=True
    )
