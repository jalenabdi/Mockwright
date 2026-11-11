import asyncio
from contextlib import asynccontextmanager

import pytest
from starlette.websockets import WebSocketDisconnect

from backend.app.main import app
from backend.app.services.deepgram import SpeechServiceError, SpeechUnavailableError, get_speech_service


class FakeTranscriptionStream:
    def __init__(self):
        self.audio: list[bytes] = []
        self.finished = False
        self._queue: asyncio.Queue | None = None

    async def start(self):
        self._queue = asyncio.Queue()

    async def send_audio(self, chunk: bytes) -> None:
        assert self._queue is not None
        self.audio.append(chunk)
        await self._queue.put({"type": "transcript", "text": f"heard {len(self.audio)}", "is_final": False})

    async def finish(self) -> None:
        assert self._queue is not None
        self.finished = True
        await self._queue.put({"type": "transcript", "text": "I led the launch.", "is_final": True})
        await self._queue.put(None)

    async def events(self):
        assert self._queue is not None
        while (event := await self._queue.get()) is not None:
            yield event


class FakeSpeechService:
    def __init__(self, error: Exception | None = None):
        self.stream = FakeTranscriptionStream()
        self.spoken: list[str] = []
        self.error = error

    @asynccontextmanager
    async def transcription(self):
        if self.error:
            raise self.error
        await self.stream.start()
        yield self.stream

    async def speak(self, text: str) -> bytes:
        if self.error:
            raise self.error
        self.spoken.append(text)
        return b"ID3-fake-mp3"


@pytest.fixture
def speech(client):
    service = FakeSpeechService()
    app.dependency_overrides[get_speech_service] = lambda: service
    return service


def _token(headers):
    return headers["Authorization"].removeprefix("Bearer ")


def test_voice_relays_audio_up_and_transcripts_down(client, auth_headers, start_interview, speech):
    interview = start_interview()

    with client.websocket_connect(f"/interviews/{interview['id']}/voice") as ws:
        ws.send_json({"token": _token(auth_headers)})
        assert ws.receive_json() == {"type": "ready"}

        ws.send_bytes(b"\x00\x01" * 160)
        assert ws.receive_json() == {"type": "transcript", "text": "heard 1", "is_final": False}

        ws.send_json({"type": "stop"})
        assert ws.receive_json() == {"type": "transcript", "text": "I led the launch.", "is_final": True}
        assert ws.receive_json() == {"type": "closed"}

    assert speech.stream.audio == [b"\x00\x01" * 160]
    assert speech.stream.finished


def test_voice_rejects_a_bad_token(client, start_interview, speech):
    interview = start_interview()
    with client.websocket_connect(f"/interviews/{interview['id']}/voice") as ws:
        ws.send_json({"token": "not-a-jwt"})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4401


def test_voice_hides_other_users_interviews(client, other_auth_headers, start_interview, speech):
    interview = start_interview()
    with client.websocket_connect(f"/interviews/{interview['id']}/voice") as ws:
        ws.send_json({"token": _token(other_auth_headers)})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4404


def test_voice_reports_when_deepgram_is_not_configured(client, auth_headers, start_interview):
    app.dependency_overrides[get_speech_service] = lambda: FakeSpeechService(
        error=SpeechUnavailableError("no key")
    )
    interview = start_interview()
    with client.websocket_connect(f"/interviews/{interview['id']}/voice") as ws:
        ws.send_json({"token": _token(auth_headers)})
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["code"] == "voice_unavailable"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_question_speech_returns_mp3_for_my_question(client, auth_headers, start_interview, speech):
    interview = start_interview()
    question = interview["current_question"]

    response = client.post(
        f"/interviews/{interview['id']}/questions/{question['id']}/speech", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"ID3-fake-mp3"
    assert speech.spoken == [question["question_text"]]


def test_question_speech_is_owner_scoped(client, other_auth_headers, auth_headers, start_interview, speech):
    interview = start_interview()
    question_id = interview["current_question"]["id"]
    mine = start_interview(target_role="Other role")

    assert client.post(
        f"/interviews/{interview['id']}/questions/{question_id}/speech", headers=other_auth_headers
    ).status_code == 404
    # A real question id under the wrong interview is also a 404.
    assert client.post(
        f"/interviews/{mine['id']}/questions/{question_id}/speech", headers=auth_headers
    ).status_code == 404


@pytest.mark.parametrize(
    ("error", "expected"), [(SpeechUnavailableError("no key"), 503), (SpeechServiceError("boom"), 502)]
)
def test_question_speech_failures_are_controlled(client, auth_headers, start_interview, error, expected):
    app.dependency_overrides[get_speech_service] = lambda: FakeSpeechService(error=error)
    interview = start_interview()
    response = client.post(
        f"/interviews/{interview['id']}/questions/{interview['current_question']['id']}/speech",
        headers=auth_headers,
    )
    assert response.status_code == expected


def test_deepgram_messages_become_simple_events():
    from backend.app.services.deepgram import to_event

    results = {
        "type": "Results",
        "is_final": True,
        "channel": {"alternatives": [{"transcript": " I owned the rollout. "}]},
    }
    assert to_event(results) == {"type": "transcript", "text": "I owned the rollout.", "is_final": True}
    assert to_event({**results, "channel": {"alternatives": [{"transcript": ""}]}}) is None
    assert to_event({"type": "SpeechStarted"}) == {"type": "speech_started"}
    assert to_event({"type": "UtteranceEnd"}) == {"type": "utterance_end"}
    assert to_event({"type": "Metadata"}) is None
