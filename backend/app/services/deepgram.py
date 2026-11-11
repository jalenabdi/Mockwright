"""Deepgram adapter: live speech-to-text and question text-to-speech.

The browser never sees DEEPGRAM_API_KEY. It streams microphone audio to our
WebSocket, and this module relays it to Deepgram's streaming /v1/listen API,
turning Deepgram's messages into a small set of events:

    {"type": "transcript", "text": "...", "is_final": bool}
    {"type": "speech_started"}
    {"type": "utterance_end"}

Audio format (sent by the browser): 16-bit little-endian PCM, mono, 16 kHz.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..config import get_settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
LISTEN_URL = "wss://api.deepgram.com/v1/listen"
SPEAK_URL = "https://api.deepgram.com/v1/speak"
KEEPALIVE_SECONDS = 5
MAX_SPEECH_CHARS = 1_000


class SpeechServiceError(RuntimeError):
    """Deepgram failed or rejected the request."""


class SpeechUnavailableError(SpeechServiceError):
    """DEEPGRAM_API_KEY is not configured."""


class TranscriptionStream(Protocol):
    async def send_audio(self, chunk: bytes) -> None: ...
    async def finish(self) -> None: ...
    def events(self) -> AsyncIterator[dict[str, Any]]: ...


class SpeechService(Protocol):
    def transcription(self) -> AbstractAsyncContextManager[TranscriptionStream]: ...

    async def open_speech(self, text: str) -> AsyncIterator[bytes]:
        """Start reading `text` aloud and return the MP3 as it arrives.

        Raises SpeechServiceError before returning if Deepgram refuses, so
        callers can still answer with an error status.
        """
        ...


_http_client: httpx.Client | None = None


def _speech_client() -> httpx.Client:
    """One shared client, so each spoken line reuses an open connection to Deepgram.

    It is the sync client, run on worker threads: in testing, httpx's async
    client held Deepgram's streamed audio back for 2-3 s, while the sync
    client hands over the first audio in about 0.2 s.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(timeout=httpx.Timeout(20, connect=5))
    return _http_client


def to_event(message: dict[str, Any]) -> dict[str, Any] | None:
    """Translate one Deepgram message into our event shape (or None to drop it)."""
    kind = message.get("type")
    if kind == "Results":
        alternatives = (message.get("channel") or {}).get("alternatives") or [{}]
        text = str(alternatives[0].get("transcript") or "").strip()
        if not text:
            return None
        return {"type": "transcript", "text": text, "is_final": bool(message.get("is_final"))}
    if kind == "SpeechStarted":
        return {"type": "speech_started"}
    if kind == "UtteranceEnd":
        return {"type": "utterance_end"}
    return None


class _DeepgramStream:
    def __init__(self, connection: ClientConnection):
        self._connection = connection
        self._finished = False

    async def send_audio(self, chunk: bytes) -> None:
        if self._finished:
            return
        try:
            await self._connection.send(chunk)
        except ConnectionClosed as error:
            raise SpeechServiceError("Deepgram closed the connection.") from error

    async def finish(self) -> None:
        """Ask Deepgram to flush the last words and close the stream."""
        if self._finished:
            return
        self._finished = True
        with contextlib.suppress(ConnectionClosed):
            await self._connection.send(json.dumps({"type": "CloseStream"}))

    async def keepalive(self) -> None:
        while not self._finished:
            await asyncio.sleep(KEEPALIVE_SECONDS)
            with contextlib.suppress(ConnectionClosed):
                await self._connection.send(json.dumps({"type": "KeepAlive"}))

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        try:
            async for raw in self._connection:
                if isinstance(raw, bytes):
                    continue
                try:
                    message = json.loads(raw)
                except ValueError:
                    continue
                if message.get("type") == "Error":
                    logger.warning("Deepgram stream error: %s", message.get("description"))
                    continue
                event = to_event(message)
                if event is not None:
                    yield event
        except ConnectionClosed:
            return


class DeepgramSpeechService:
    def __init__(self, api_key: str, stt_model: str, tts_model: str):
        self._api_key = api_key
        self._stt_model = stt_model
        self._tts_model = tts_model

    def _require_key(self) -> str:
        if not self._api_key:
            raise SpeechUnavailableError("DEEPGRAM_API_KEY is not set.")
        return self._api_key

    @asynccontextmanager
    async def transcription(self) -> AsyncIterator[TranscriptionStream]:
        api_key = self._require_key()
        query = urlencode(
            {
                "model": self._stt_model,
                "language": "en-US",
                "encoding": "linear16",
                "sample_rate": SAMPLE_RATE,
                "channels": 1,
                "interim_results": "true",
                "smart_format": "true",
                "punctuate": "true",
                "endpointing": 300,
                "utterance_end_ms": 1000,
                "vad_events": "true",
            }
        )
        try:
            connection = await connect(
                f"{LISTEN_URL}?{query}",
                additional_headers={"Authorization": f"Token {api_key}"},
                open_timeout=10,
                max_size=2**20,
            )
        except (OSError, WebSocketException, TimeoutError) as error:
            raise SpeechServiceError(f"Could not connect to Deepgram: {type(error).__name__}") from error

        stream = _DeepgramStream(connection)
        keepalive = asyncio.create_task(stream.keepalive())
        try:
            yield stream
        finally:
            keepalive.cancel()
            with contextlib.suppress(Exception):
                await connection.close()

    async def open_speech(self, text: str) -> AsyncIterator[bytes]:
        api_key = self._require_key()
        client = _speech_client()
        request = client.build_request(
            "POST",
            SPEAK_URL,
            params={"model": self._tts_model, "encoding": "mp3"},
            headers={"Authorization": f"Token {api_key}"},
            json={"text": text[:MAX_SPEECH_CHARS]},
        )
        try:
            response = await run_in_threadpool(client.send, request, stream=True)
        except httpx.HTTPError as error:
            raise SpeechServiceError(f"Deepgram TTS request failed: {type(error).__name__}") from error
        if response.status_code != 200:
            response.close()
            raise SpeechServiceError(f"Deepgram TTS returned {response.status_code}.")

        async def audio() -> AsyncIterator[bytes]:
            try:
                async for chunk in iterate_in_threadpool(response.iter_bytes()):
                    yield chunk
            except httpx.HTTPError as error:
                logger.warning("Deepgram TTS stream broke off: %s", type(error).__name__)
            finally:
                await run_in_threadpool(response.close)

        return audio()


def get_speech_service() -> SpeechService:
    """FastAPI dependency."""
    settings = get_settings()
    return DeepgramSpeechService(
        settings.deepgram_api_key, settings.deepgram_stt_model, settings.deepgram_tts_model
    )
