"""Answer videos: upload, playback, ownership, limits, and deleting interviews."""
import pytest

from backend.app.main import app
from backend.app.services.recording_store import RecordingStore, get_recording_store

VIDEO = b"\x1a\x45\xdf\xa3" + b"fake webm bytes" * 100


@pytest.fixture
def store(client, tmp_path):
    recording_store = RecordingStore(tmp_path / "recordings", max_bytes=10_000)
    app.dependency_overrides[get_recording_store] = lambda: recording_store
    return recording_store


def _url(interview, question_id=None):
    question_id = question_id or interview["current_question"]["id"]
    return f"/interviews/{interview['id']}/questions/{question_id}/recording"


def _upload(client, url, headers, body=VIDEO, content_type="video/webm;codecs=vp9,opus", **params):
    return client.put(url, content=body, headers={**headers, "Content-Type": content_type}, params=params)


def test_upload_then_play_back(client, auth_headers, start_interview, store):
    interview = start_interview()
    url = _url(interview)

    response = _upload(client, url, auth_headers, duration_seconds=42.5)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "question_id": interview["current_question"]["id"],
        "mime_type": "video/webm",
        "size_bytes": len(VIDEO),
        "duration_seconds": 42.5,
    }

    played = client.get(url, headers=auth_headers)
    assert played.status_code == 200
    assert played.content == VIDEO
    assert played.headers["content-type"] == "video/webm"

    files = list((store.root).rglob("*.webm"))
    assert [f.name for f in files] == ["q1.webm"]


def test_detail_marks_questions_with_a_recording(client, auth_headers, start_interview, answer_current, store):
    interview = start_interview()
    first_url = _url(interview)
    interview, _ = answer_current(interview)
    _upload(client, first_url, auth_headers)

    detail = client.get(f"/interviews/{interview['id']}", headers=auth_headers).json()
    assert [q["has_recording"] for q in detail["questions"]] == [True, False]


def test_upload_again_replaces_the_video(client, auth_headers, start_interview, store):
    interview = start_interview()
    url = _url(interview)
    _upload(client, url, auth_headers)
    _upload(client, url, auth_headers, body=b"second take", content_type="video/mp4")

    played = client.get(url, headers=auth_headers)
    assert played.content == b"second take"
    assert played.headers["content-type"] == "video/mp4"
    assert [f.name for f in store.root.rglob("q1.*")] == ["q1.mp4"]


def test_rejects_non_video_uploads(client, auth_headers, start_interview, store):
    interview = start_interview()
    response = _upload(client, _url(interview), auth_headers, content_type="text/plain")
    assert response.status_code == 415


def test_rejects_empty_and_oversized_uploads(client, auth_headers, start_interview, store):
    interview = start_interview()
    url = _url(interview)
    _upload(client, url, auth_headers)

    assert _upload(client, url, auth_headers, body=b"").status_code == 422
    assert _upload(client, url, auth_headers, body=b"x" * 20_000).status_code == 413

    # The earlier good video is still there, and no partial files are left behind.
    assert client.get(url, headers=auth_headers).content == VIDEO
    assert [f.name for f in store.root.rglob("*") if f.is_file()] == ["q1.webm"]


def test_question_must_belong_to_the_interview(client, auth_headers, start_interview, store):
    first = start_interview()
    second = start_interview()
    url = _url(first, question_id=second["current_question"]["id"])
    assert _upload(client, url, auth_headers).status_code == 404


def test_missing_recording_is_404(client, auth_headers, start_interview, store):
    interview = start_interview()
    assert client.get(_url(interview), headers=auth_headers).status_code == 404


def test_other_users_cannot_upload_or_watch(client, auth_headers, other_auth_headers, start_interview, store):
    interview = start_interview()
    url = _url(interview)
    _upload(client, url, auth_headers)

    assert _upload(client, url, other_auth_headers).status_code == 404
    assert client.get(url, headers=other_auth_headers).status_code == 404
    assert client.get(url).status_code == 401


def test_delete_interview_removes_everything(
    client, auth_headers, start_interview, answer_current, store
):
    interview = start_interview()
    url = _url(interview)
    interview, _ = answer_current(interview)
    _upload(client, url, auth_headers)
    kept = start_interview()

    response = client.delete(f"/interviews/{interview['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get(f"/interviews/{interview['id']}", headers=auth_headers).status_code == 404
    assert [i["id"] for i in client.get("/interviews", headers=auth_headers).json()] == [kept["id"]]
    assert list(store.root.rglob("*.webm")) == []


def test_delete_interview_removes_its_feedback(client, auth_headers, start_interview, answer_current, store):
    from backend.app.services.gemini_feedback import get_feedback_generator
    from backend.app.schemas.feedback import FeedbackReport

    class FixedFeedback:
        def generate(self, context, turns):
            return FeedbackReport(
                relevance_score=10, star_structure_score=10, specificity_score=10,
                individual_contribution_score=10, communication_score=10, total_score=50,
                strengths=["Clear"], improvements=["More numbers"], next_step="Practise STAR.",
            )

    app.dependency_overrides[get_feedback_generator] = lambda: FixedFeedback()
    interview = start_interview()
    for _ in range(5):
        interview, _ = answer_current(interview)
    assert client.post(f"/interviews/{interview['id']}/feedback", headers=auth_headers).status_code == 201

    assert client.delete(f"/interviews/{interview['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/interviews/{interview['id']}/feedback", headers=auth_headers).status_code == 404


def test_cannot_delete_someone_elses_interview(client, auth_headers, other_auth_headers, start_interview, store):
    interview = start_interview()
    assert client.delete(f"/interviews/{interview['id']}", headers=other_auth_headers).status_code == 404
    assert client.get(f"/interviews/{interview['id']}", headers=auth_headers).status_code == 200
