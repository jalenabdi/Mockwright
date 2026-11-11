"""Bridge Deepgram conversation events to persisted interview answers."""

import asyncio
import logging

from .voice_answers import VoiceAnswerRecorder

logger = logging.getLogger(__name__)


async def handle_voice_event(
    interview_id: int,
    user_id: int,
    event: dict,
) -> bool:
    """Save final user transcripts and report when the fifth answer is saved."""
    outcome = await asyncio.to_thread(
        VoiceAnswerRecorder(interview_id).handle_event,
        event,
    )
    if outcome is None:
        return False
    if outcome.saved:
        logger.info(
            "Saved voice answer for interview %s and user %s (%s/%s)",
            interview_id,
            user_id,
            outcome.answered_count,
            outcome.total_questions,
        )
    elif outcome.reason not in (None, "blank_transcript"):
        logger.warning(
            "Could not save voice answer for interview %s: %s",
            interview_id,
            outcome.reason,
        )
    return outcome.interview_completed
