from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .interview_question import InterviewQuestion


class Recording(Base):
    """A video of the candidate answering one question.

    The video itself lives on disk (see services/recording_store.py); this row
    records where, so the database stays small.
    """

    __tablename__ = "recordings"
    __table_args__ = (
        UniqueConstraint("interview_question_id", name="uq_recordings_interview_question_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_question_id: Mapped[int] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE")
    )
    # Path relative to the recordings folder, e.g. "3/12/q1.webm".
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    duration_seconds: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question: Mapped[InterviewQuestion] = relationship(back_populates="recording")
