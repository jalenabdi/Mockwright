from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .feedback import FeedbackReport


class ExperienceLevel(str, Enum):
    """The four experience levels Mockwright supports."""

    INTERN = "intern"
    ENTRY_LEVEL = "entry-level"
    JUNIOR = "junior"
    SENIOR = "senior"


class StartInterviewRequest(BaseModel):
    """Settings a user submits to start a new interview."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "target_role": "Software Engineer",
                    "experience_level": "entry-level",
                    "job_description": "Build and maintain backend APIs in Python.",
                }
            ]
        },
    )

    target_role: str = Field(min_length=1, max_length=100)
    experience_level: ExperienceLevel
    job_description: str | None = Field(default=None, max_length=5000)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_order: int
    question_text: str


class QuestionWithAnswer(QuestionOut):
    answer_text: str | None = None


class InterviewSummary(BaseModel):
    id: int
    target_role: str
    experience_level: str
    status: str
    answered_count: int
    total_questions: int
    created_at: datetime
    total_score: int | None = None

    @field_validator("created_at")
    @classmethod
    def assume_utc(cls, value: datetime) -> datetime:
        # SQLite drops the timezone; every stored time is UTC.
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class InterviewDetail(InterviewSummary):
    job_description: str | None
    current_question_position: int
    current_question: QuestionOut | None
    questions: list[QuestionWithAnswer]
    feedback: FeedbackReport | None = None


class CurrentQuestionResponse(BaseModel):
    interview_id: int
    current_position: int
    total_questions: int
    status: str
    question: QuestionOut
