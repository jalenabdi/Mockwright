from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionGrade(BaseModel):
    """The grade for one answer: a 0-100 score and one sentence on why."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    question_number: int = Field(ge=1, description="The question's position in the interview, from 1.")
    score: int = Field(ge=0, le=100, description="How strong this one answer was, from 0 to 100.")
    comment: str = Field(min_length=1, description="One sentence explaining the score.")


class FeedbackReport(BaseModel):
    """Feedback for a completed interview.

    Each category is scored from 0 to 20: 0-4 is absent or very weak, 5-9 is
    limited, 10-14 is mixed, 15-17 is strong, and 18-20 is exceptional.
    The total is the sum of the five category scores.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    relevance_score: int = Field(
        ge=0,
        le=20,
        description="How directly and completely the answer addresses the question.",
    )
    star_structure_score: int = Field(
        ge=0,
        le=20,
        description=(
            "How clearly the answer establishes the Situation and Task, explains "
            "the Action, and states the Result."
        ),
    )
    specificity_score: int = Field(
        ge=0,
        le=20,
        description=(
            "How much concrete context, examples, decisions, or outcomes support "
            "the answer; metrics help but are not required."
        ),
    )
    individual_contribution_score: int = Field(
        ge=0,
        le=20,
        description=(
            "How clearly the candidate identifies their own actions and impact, "
            "rather than attributing work only to a team."
        ),
    )
    communication_score: int = Field(
        ge=0,
        le=20,
        description="How clearly, logically, and concisely the answer is communicated.",
    )
    total_score: int = Field(
        ge=0,
        le=100,
        description="The sum of the five category scores.",
    )
    strengths: list[str] = Field(
        max_length=3,
        description="Up to three specific strengths supported by the candidate's answers.",
    )
    improvements: list[str] = Field(
        max_length=3,
        description="Up to three specific, actionable areas for improvement.",
    )
    next_step: str = Field(
        min_length=1,
        description="One concise, actionable recommendation for continued practice.",
    )
    question_grades: list[QuestionGrade] = Field(
        default_factory=list,
        description="One grade per answer, in question order. Empty for reports saved before grades existed.",
    )

    @model_validator(mode="after")
    def validate_total(self) -> "FeedbackReport":
        expected_total = (
            self.relevance_score
            + self.star_structure_score
            + self.specificity_score
            + self.individual_contribution_score
            + self.communication_score
        )
        if self.total_score != expected_total:
            raise ValueError(
                "total_score must equal the sum of the individual score fields"
            )
        return self
