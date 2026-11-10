"""Turns spoken answers from the Deepgram Voice Agent into saved interview answers.

The WebSocket relay creates one VoiceAnswerRecorder per voice session and
hands it every JSON event that Deepgram sends. For each final user transcript
the recorder saves an answer through the same save_answer service the typed
answer flow uses, so progress advances exactly the same way. After the last
question is answered, the outcome says the interview is completed and the relay
should end the session.

Deepgram sends the user's words as:
    {"type": "ConversationText", "role": "user", "content": "..."}

Example use inside the async relay loop (the database calls are blocking, so
they run in a worker thread):

    recorder = VoiceAnswerRecorder(interview.id)
    ...
    outcome = await asyncio.to_thread(recorder.handle_event, event)
    if outcome and outcome.interview_completed:
        ...  # let the interviewer's goodbye finish, then close the session
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.interview import Interview
from ..models.interview_question import InterviewQuestion
from .exceptions import InterviewAlreadyCompletedError, InterviewServiceError
from .interview_service import STATUS_COMPLETED, save_answer


@dataclass
class VoiceAnswerOutcome:
    """What happened to one user transcript."""

    saved: bool
    interview_completed: bool = False
    answered_count: int = 0
    total_questions: int = 0
    next_question: str | None = None
    reason: str | None = None  # why nothing was saved, for logging


class VoiceAnswerRecorder:
    def __init__(
        self,
        interview_id: int,
        session_factory: Callable[[], Session] = SessionLocal,
    ):
        self.interview_id = interview_id
        self._session_factory = session_factory

    def handle_event(self, event: dict) -> VoiceAnswerOutcome | None:
        """Save a user transcript as the answer to the current question.

        Returns None for any event that is not a user transcript (agent text,
        audio events, and so on), so the relay can pass every event through.
        """
        if event.get("type") != "ConversationText" or event.get("role") != "user":
            return None

        transcript = str(event.get("content") or "").strip()
        if not transcript:
            return VoiceAnswerOutcome(saved=False, reason="blank_transcript")

        with self._session_factory() as db:
            interview = db.get(Interview, self.interview_id)
            if interview is None:
                return VoiceAnswerOutcome(saved=False, reason="interview_not_found")
            if interview.status == STATUS_COMPLETED:
                return VoiceAnswerOutcome(
                    saved=False, interview_completed=True, reason="already_completed"
                )

            question = db.scalar(
                select(InterviewQuestion).where(
                    InterviewQuestion.interview_id == self.interview_id,
                    InterviewQuestion.question_order == interview.current_question_position,
                )
            )
            if question is None:
                return VoiceAnswerOutcome(saved=False, reason="no_current_question")

            try:
                result = save_answer(db, self.interview_id, question.id, transcript)
            except InterviewAlreadyCompletedError:
                return VoiceAnswerOutcome(
                    saved=False, interview_completed=True, reason="already_completed"
                )
            except InterviewServiceError as error:
                return VoiceAnswerOutcome(saved=False, reason=type(error).__name__)

            return VoiceAnswerOutcome(
                saved=True,
                interview_completed=result.status == STATUS_COMPLETED,
                answered_count=result.answered_count,
                total_questions=result.total_questions,
                next_question=result.next_question.question_text if result.next_question else None,
            )