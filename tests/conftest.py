"""Shared fixtures: an isolated in-memory database and fake AI services.

No test talks to Postgres, Gemini or Deepgram.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-0123456789")
os.environ["GEMINI_API_KEY"] = ""
os.environ["DEEPGRAM_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Base


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    def _get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class RecordingQuestionGenerator:
    """Writes predictable questions and records what it was shown.

    Put texts in `follow_ups` to have them asked, one per answer, whenever a
    follow-up is allowed. By default it never follows up.
    """

    def __init__(self):
        self.calls = []
        self.step_calls = []
        self.follow_ups: list[str] = []

    def next_question(self, context, history):
        self.calls.append((context, list(history)))
        return f"Question {len(history) + 1} for {context.target_role}?"

    def next_step(self, context, history, *, can_follow_up, is_last):
        from backend.app.services.question_generator import NextStep

        self.step_calls.append(
            {"context": context, "history": list(history), "can_follow_up": can_follow_up, "is_last": is_last}
        )
        if can_follow_up and self.follow_ups:
            return NextStep(follow_up=self.follow_ups.pop(0))
        return NextStep(next_question=None if is_last else self.next_question(context, history))


@pytest.fixture
def question_generator(client):
    from backend.app.services.question_generator import get_question_generator

    generator = RecordingQuestionGenerator()
    app.dependency_overrides[get_question_generator] = lambda: generator
    return generator


def _signed_in_headers(client, email):
    client.post("/auth/register", json={"email": email, "password": "correct-horse"})
    token = client.post(
        "/auth/token", data={"username": email, "password": "correct-horse"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client):
    return _signed_in_headers(client, "ada@example.com")


@pytest.fixture
def other_auth_headers(client):
    return _signed_in_headers(client, "grace@example.com")


START_PAYLOAD = {
    "target_role": "Software Engineer",
    "experience_level": "intern",
    "job_description": "Build internal tools in Python.",
}


@pytest.fixture
def start_interview(client, auth_headers, question_generator):
    def _start(headers=None, **overrides):
        response = client.post(
            "/interviews/start", json={**START_PAYLOAD, **overrides}, headers=headers or auth_headers
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _start


@pytest.fixture
def answer_current(client, auth_headers):
    def _answer(interview, text="I owned the migration and cut build time by 40%.", headers=None):
        question_id = interview["current_question"]["id"]
        response = client.post(
            f"/interviews/{interview['id']}/answers",
            json={"question_id": question_id, "answer_text": text},
            headers=headers or auth_headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        interview = {**interview, "current_question": body["next_question"], "status": body["status"]}
        return interview, body

    return _answer
