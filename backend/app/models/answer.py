from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint(
            "interview_question_id",
            name="uq_answers_interview_question_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    question: Mapped["InterviewQuestion"] = relationship(
        "InterviewQuestion",
        back_populates="answer",
    )
