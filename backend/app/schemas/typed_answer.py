from pydantic import BaseModel, Field, field_validator

from .interview import FollowUpOut, QuestionOut


class TypedAnswerInput(BaseModel):
    """An answer to the interview's current question (typed, or a voice transcript)."""

    question_id: int
    # Set when answering a follow-up on question_id instead of the question itself.
    follow_up_id: int | None = None
    answer_text: str = Field(max_length=10_000)

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, incoming_text: str) -> str:
        """Reject empty or whitespace-only answers."""
        if not incoming_text or not incoming_text.strip():
            raise ValueError("Answer text cannot be empty or whitespace.")
        return incoming_text.strip()


class TypedAnswerReturn(BaseModel):
    """The saved answer record (a follow-up's id when it answered a follow-up)."""

    id: int
    question_id: int
    answer_text: str


class SubmitAnswerResponse(BaseModel):
    answer: TypedAnswerReturn
    status: str
    answered_count: int
    total_questions: int
    # At most one is set: a follow-up on the same question, or the next question.
    # Neither is set once the interview is completed.
    follow_up: FollowUpOut | None = None
    next_question: QuestionOut | None
