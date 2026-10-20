# backend/app/models/interview.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .base import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    target_role = Column(String, nullable=False)
    experience_level = Column(String, nullable=False)
    job_description = Column(String, nullable=True)
    status = Column(String, default="in_progress", nullable=False)
    current_question_position = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
