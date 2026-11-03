from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeedbackReport(BaseModel):
    """Schema returned from the AI feedback generator for a completed interview."""

    model_config = ConfigDict(from_attributes=True)

    relevance_score: int = Field(ge=0, le=20)
    star_structure_score: int = Field(ge=0, le=20)
    specificity_score: int = Field(ge=0, le=20)
    individual_contribution_score: int = Field(ge=0, le=20)
    communication_score: int = Field(ge=0, le=20)
    total_score: int = Field(ge=0, le=100)
    strengths: list[str]
    improvements: list[str]
    next_step: str

    @model_validator(mode="after")
    def validate_total(self):
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
