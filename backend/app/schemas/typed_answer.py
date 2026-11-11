from pydantic import BaseModel, Field, field_validator

from .interview import QuestionOut


class TypedAnswerInput(BaseModel):
    """An answer to the interview's current question (typed, or a voice transcript)."""

    question_id: int
    answer_text: str = Field(max_length=10_000)

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, incoming_text: str) -> str:
        """Reject empty or whitespace-only answers."""
        if not incoming_text or not incoming_text.strip():
            raise ValueError("Answer text cannot be empty or whitespace.")
        return incoming_text.strip()


class TypedAnswerReturn(BaseModel):
    """The saved answer record."""

    id: int
    question_id: int
    answer_text: str


class SubmitAnswerResponse(BaseModel):
    answer: TypedAnswerReturn
    status: str
    answered_count: int
    total_questions: int
    next_question: QuestionOut | None
