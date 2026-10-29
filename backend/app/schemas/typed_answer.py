from pydantic import BaseModel, ConfigDict, field_validator


class TypedAnswerInput(BaseModel):
    """A typed answer input for a specific question in an interview."""

    question_id: int
    answer_text: str

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, incoming_text: str) -> str:
        """Validate that the answer text is not empty or whitespace."""
        if not incoming_text or not incoming_text.strip():
            raise ValueError("Answer text cannot be empty or whitespace.")
        return incoming_text.strip()


class TypedAnswerReturn(BaseModel):
    """The saved answer record returned after a typed answer is created."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_text: str
