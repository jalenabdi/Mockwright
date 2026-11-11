from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .feedback import Feedback
    from .interview_question import InterviewQuestion
    from .user import User

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    target_role: Mapped[str] = mapped_column(String(100))
    experience_level: Mapped[str] = mapped_column(String(20))
    job_description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_IN_PROGRESS)
    # 1-based order of the question being answered; total + 1 once completed.
    current_question_position: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship(back_populates="interviews")
    questions: Mapped[list[InterviewQuestion]] = relationship(
        back_populates="interview",
        order_by="InterviewQuestion.question_order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedback: Mapped[Feedback | None] = relationship(
        back_populates="interview", cascade="all, delete-orphan", passive_deletes=True
    )
