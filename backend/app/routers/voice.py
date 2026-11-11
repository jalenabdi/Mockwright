"""Live voice answers and spoken questions.

WebSocket protocol for /interviews/{id}/voice:
  client -> {"token": "<jwt>"}               must be the first message, within 10 s
  server -> {"type": "ready"}                 Deepgram is listening
  client -> <binary PCM16 mono 16 kHz>        microphone audio, repeatedly
  server -> {"type": "transcript", "text", "is_final"}
            {"type": "speech_started"} / {"type": "utterance_end"}
  client -> {"type": "stop"}                  finish: final words are flushed
  server -> {"type": "closed"}                then the socket closes (1000)

Errors: {"type": "error", "code", "message"} then close.
Close codes: 4401 bad auth, 4404 unknown/not-yours interview, 4409 completed.

The transcript is not saved here. The user reviews it and saves it through
POST /interviews/{id}/answers, the same path typed answers use.
"""
import asyncio
import contextlib
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, WebSocket, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect, WebSocketState

from ..database import get_db
from ..dependencies import DbSession, OwnedInterview, find_owned_interview, user_from_token
from ..models import STATUS_IN_PROGRESS, InterviewQuestion
from ..services.deepgram import (
    SpeechService,
    SpeechServiceError,
    SpeechUnavailableError,
    TranscriptionStream,
    get_speech_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interviews", tags=["Voice"])

Speech = Annotated[SpeechService, Depends(get_speech_service)]

AUTH_TIMEOUT_SECONDS = 10
MAX_AUDIO_CHUNK_BYTES = 64 * 1024

CLOSE_UNAUTHORIZED = 4401
CLOSE_NOT_FOUND = 4404
CLOSE_COMPLETED = 4409


async def _close(websocket: WebSocket, code: int = 1000) -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        with contextlib.suppress(RuntimeError):
            await websocket.close(code=code)


async def _authorize(websocket: WebSocket, interview_id: int, db: Session) -> int | None:
    """Return the close code to use, or None if the user may stream audio."""
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT_SECONDS)
        token = json.loads(raw).get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("missing token")
    except (asyncio.TimeoutError, ValueError, AttributeError, KeyError, WebSocketDisconnect):
        return CLOSE_UNAUTHORIZED

    try:
        user = user_from_token(token, db)
        if user is None:
            return CLOSE_UNAUTHORIZED
        interview = find_owned_interview(db, interview_id, user.id)
        if interview is None:
            return CLOSE_NOT_FOUND
        if interview.status != STATUS_IN_PROGRESS:
            return CLOSE_COMPLETED
        return None
    finally:
        db.close()  # don't hold a connection for the whole voice session


async def _client_to_deepgram(websocket: WebSocket, stream: TranscriptionStream) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            await stream.finish()
            return
        chunk = message.get("bytes")
        if chunk is not None:
            if len(chunk) > MAX_AUDIO_CHUNK_BYTES:
                await stream.finish()
                return
            await stream.send_audio(chunk)
            continue
        text = message.get("text")
        if text is not None:
            try:
                data = json.loads(text)
            except ValueError:
                continue
            if isinstance(data, dict) and data.get("type") == "stop":
                await stream.finish()
                return


async def _deepgram_to_client(websocket: WebSocket, stream: TranscriptionStream) -> None:
    async for event in stream.events():
        await websocket.send_json(event)


@router.websocket("/{interview_id}/voice")
async def interview_voice(
    websocket: WebSocket,
    interview_id: int,
    db: Annotated[Session, Depends(get_db)],
    speech: Speech,
) -> None:
    await websocket.accept()

    close_code = await _authorize(websocket, interview_id, db)
    if close_code is not None:
        await _close(websocket, close_code)
        return

    try:
        async with speech.transcription() as stream:
            await websocket.send_json({"type": "ready"})
            uplink = asyncio.create_task(_client_to_deepgram(websocket, stream))
            downlink = asyncio.create_task(_deepgram_to_client(websocket, stream))
            # Deepgram ends the downlink after a stop (or on its own); then we finish.
            done, _ = await asyncio.wait({uplink, downlink}, return_when=asyncio.FIRST_EXCEPTION)
            if downlink not in done:
                await downlink
            uplink.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await uplink
            for task in done:
                if task.exception():
                    raise task.exception()  # type: ignore[misc]
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "closed"})
    except SpeechUnavailableError:
        await _send_error(websocket, "voice_unavailable", "Voice answers aren't set up on this server. Switch to Text.")
        await _close(websocket, 1011)
        return
    except SpeechServiceError as error:
        logger.warning("Deepgram session failed for interview %s: %s", interview_id, error)
        await _send_error(websocket, "voice_failed", "The voice connection dropped. Try again or switch to Text.")
        await _close(websocket, 1011)
        return
    except WebSocketDisconnect:
        return

    await _close(websocket, 1000)


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await websocket.send_json({"type": "error", "code": code, "message": message})


@router.post(
    "/{interview_id}/questions/{question_id}/speech",
    response_class=Response,
    responses={200: {"content": {"audio/mpeg": {}}}},
)
async def question_speech(
    question_id: int,
    interview: OwnedInterview,
    db: DbSession,
    speech: Speech,
) -> Response:
    """Read one of the interview's questions aloud (MP3 from Deepgram Aura)."""
    question_text = db.scalar(
        select(InterviewQuestion.question_text).where(
            InterviewQuestion.id == question_id,
            InterviewQuestion.interview_id == interview.id,
        )
    )
    if question_text is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    try:
        audio = await speech.speak(question_text)
    except SpeechUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spoken questions aren't set up on this server.",
        )
    except SpeechServiceError as error:
        logger.warning("Question speech failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not read the question aloud right now.",
        )
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=3600"})
