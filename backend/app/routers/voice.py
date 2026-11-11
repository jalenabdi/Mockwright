import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.websockets import WebSocketDisconnect, WebSocketState
from websockets.exceptions import WebSocketException

from ..database import SessionLocal
from ..dependencies import get_current_user
from ..models import Interview, InterviewQuestion

from ..services.deepgram import DeepgramError, open_voice_session
from ..services.voice_events import handle_voice_event

logger = logging.getLogger(__name__)
router = APIRouter()

AUTH_TIMEOUT_SECONDS = 10
MAX_AUDIO_CHUNK_BYTES = 64 * 1024


async def _close(websocket: WebSocket, code: int = 1000) -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        try:
            await websocket.close(code=code)
        except RuntimeError:
            pass


async def _fail(websocket: WebSocket, detail: str) -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        try:
            await websocket.send_json({"type": "error", "detail": detail})
        except RuntimeError:
            pass
    await _close(websocket, 1011)


async def _client_to_deepgram(websocket: WebSocket, dg) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return
        if message.get("bytes") is not None:
            chunk = message["bytes"]
            if len(chunk) > MAX_AUDIO_CHUNK_BYTES:
                await _close(websocket, 1009)
                return
            await dg.send_audio(chunk)
        elif message.get("text") is not None:
            try:
                data = json.loads(message["text"])
            except ValueError:
                await websocket.send_json(
                    {"type": "error", "detail": "Expected a JSON control message."}
                )
                continue
            if isinstance(data, dict) and data.get("type") == "stop":
                return
            # Other client JSON is ignored on purpose, never forwarded to Deepgram


async def _deepgram_to_client(websocket: WebSocket, dg, interview_id: int, user_id: int) -> None:
    async for event in dg.receive():
        if isinstance(event, (bytes, bytearray)):
            await websocket.send_bytes(bytes(event))
            continue
        await websocket.send_json(event)
        if await handle_voice_event(interview_id, user_id, event):
            await websocket.send_json({"type": "interview_complete"})
            return


@router.websocket("/interviews/{interview_id}/voice")
async def interview_voice(websocket: WebSocket, interview_id: int):
    await websocket.accept()

    # 1. First message must be {"token": "<jwt>"}
    try:
        raw_message = await asyncio.wait_for(websocket.receive_text(), AUTH_TIMEOUT_SECONDS)
        auth_message = json.loads(raw_message)
        if not isinstance(auth_message, dict):
            raise ValueError("authentication message must be a JSON object")
        token = auth_message.get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("missing token")
    except (TimeoutError, WebSocketDisconnect, ValueError) as exc:
        logger.warning("Bad voice auth message for interview %s: %s", interview_id, type(exc).__name__)
        await _close(websocket, 4401)
        return

    # 2. Verify token, ownership and status with a short-lived DB session
    try:
        with SessionLocal() as db:
            try:
                user = get_current_user(token=token, db=db)
            except HTTPException:
                await _close(websocket, 4401)
                return

            interview = db.get(Interview, interview_id)
            if interview is None or interview.user_id != user.id:
                await _close(websocket, 4404)
                return
            if interview.status != "in_progress":
                await _close(websocket, 4409)
                return

            questions = list(db.scalars(
                select(InterviewQuestion.question_text)
                .where(InterviewQuestion.interview_id == interview_id)
                .order_by(InterviewQuestion.question_order)
            ))
            user_id = user.id
    except SQLAlchemyError:
        logger.exception("Could not load interview %s for voice session", interview_id)
        await _fail(websocket, "Could not load this interview. Please try again.")
        return

    if len(questions) != 5:
        logger.error(
            "Interview %s has %s questions; voice interviews require exactly five",
            interview_id,
            len(questions),
        )
        await _fail(websocket, "This interview does not have the five required questions.")
        return

    # 3. Connect to Deepgram and relay both directions
    try:
        # Open the Deepgram voice session for the interview
        async with open_voice_session(questions) as dg:
            await websocket.send_json({"type": "ready"})
            # Start the bidirectional relay between the client and Deepgram
            tasks = {
                asyncio.create_task(_client_to_deepgram(websocket, dg)),
                asyncio.create_task(_deepgram_to_client(websocket, dg, interview_id, user_id)),
            }
            # Wait for either the client or Deepgram to finish first
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            # Cancel the other task if one finishes first
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            # Check for exceptions in the completed tasks
            for task in done:
                error = task.exception()
                if error is not None:
                    raise error
    except DeepgramError:
        logger.warning("Deepgram session failed for interview %s", interview_id)
        await _fail(websocket, "The voice service is unavailable. Please try again.")
        return
    except WebSocketDisconnect:
        pass
    except (SQLAlchemyError, OSError, RuntimeError, TimeoutError, WebSocketException) as exc:
        logger.exception(
            "Voice session failed for interview %s: %s",
            interview_id,
            type(exc).__name__,
        )
        await _fail(websocket, "The voice session encountered an error. Please reconnect.")
        return

    await _close(websocket, 1000)