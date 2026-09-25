from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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

    target_role: str = Field(
        min_length=1,
        max_length=100,
        description="The job title the user is practicing for.",
    )
    experience_level: ExperienceLevel = Field(
        description="One of: intern, entry-level, junior, senior.",
    )
    job_description: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional job description to tailor the interview.",
    )