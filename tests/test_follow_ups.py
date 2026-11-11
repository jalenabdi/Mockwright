"""The interviewer can ask up to two follow-ups on each of the five questions."""
import pytest

from backend.app.services.question_generator import MAX_FOLLOW_UPS, Turn


def _answer_follow_up(client, headers, interview_id, question_id, follow_up_id, text="I chose Postgres myself."):
    return client.post(
        f"/interviews/{interview_id}/answers",
        json={"question_id": question_id, "follow_up_id": follow_up_id, "answer_text": text},
        headers=headers,
    )


def test_an_answer_can_get_a_follow_up_before_the_next_question(
    client, auth_headers, start_interview, answer_current, question_generator
):
    interview = start_interview()
    question = interview["current_question"]
    question_generator.follow_ups = ["Interesting. What did you do yourself?"]

    _, body = answer_current(interview, text="We moved to Postgres.")

    assert body["status"] == "in_progress"
    assert body["next_question"] is None
    assert body["follow_up"]["question_text"] == "Interesting. What did you do yourself?"
    assert body["follow_up"]["question_id"] == question["id"]
    assert body["answered_count"] == 1

    response = _answer_follow_up(client, auth_headers, interview["id"], question["id"], body["follow_up"]["id"])
    assert response.status_code == 201, response.text
    after = response.json()
    assert after["follow_up"] is None
    assert after["next_question"]["question_order"] == 2

    # The next question was written with the follow-up exchange in view.
    last_history = question_generator.step_calls[-1]["history"]
    assert last_history == [
        Turn(
            question=question["question_text"],
            answer="We moved to Postgres.",
            follow_ups=(Turn(question="Interesting. What did you do yourself?", answer="I chose Postgres myself."),),
        )
    ]


def test_each_question_gets_at_most_two_follow_ups(client, auth_headers, start_interview, answer_current, question_generator):
    interview = start_interview()
    question_id = interview["current_question"]["id"]
    question_generator.follow_ups = ["First probe?", "Second probe?", "Third probe?"]

    _, body = answer_current(interview)
    for expected in ["Second probe?", None]:
        body = _answer_follow_up(client, auth_headers, interview["id"], question_id, body["follow_up"]["id"]).json()
        assert (body["follow_up"] or {}).get("question_text") == expected

    assert body["next_question"]["question_order"] == 2
    assert question_generator.step_calls[-1]["can_follow_up"] is False
    assert MAX_FOLLOW_UPS == 2


def test_the_interview_ends_only_after_the_last_follow_up(client, auth_headers, start_interview, answer_current, question_generator):
    interview = start_interview()
    for _ in range(4):
        interview, _ = answer_current(interview)
    last_question_id = interview["current_question"]["id"]
    question_generator.follow_ups = ["One more thing: what was the result?"]

    interview, body = answer_current(interview)
    assert body["status"] == "in_progress"
    assert question_generator.step_calls[-1]["is_last"] is True

    done = _answer_follow_up(client, auth_headers, interview["id"], last_question_id, body["follow_up"]["id"]).json()
    assert done["status"] == "completed"
    assert done["next_question"] is None and done["follow_up"] is None


def test_follow_up_answers_must_be_for_the_open_follow_up(client, auth_headers, start_interview, answer_current, question_generator):
    interview = start_interview()
    question_id = interview["current_question"]["id"]
    question_generator.follow_ups = ["Why that approach?"]
    _, body = answer_current(interview)
    follow_up_id = body["follow_up"]["id"]

    assert _answer_follow_up(client, auth_headers, interview["id"], question_id, follow_up_id + 999).status_code == 400
    assert _answer_follow_up(client, auth_headers, interview["id"], question_id, follow_up_id).status_code == 201
    assert _answer_follow_up(client, auth_headers, interview["id"], question_id, follow_up_id).status_code == 409


def test_an_open_follow_up_survives_a_refresh(client, auth_headers, start_interview, answer_current, question_generator):
    interview = start_interview()
    question_generator.follow_ups = ["Who else was involved?"]
    answer_current(interview)

    current = client.get(f"/interviews/{interview['id']}/current-question", headers=auth_headers).json()
    assert current["question"]["question_order"] == 1
    assert current["follow_up"]["question_text"] == "Who else was involved?"

    detail = client.get(f"/interviews/{interview['id']}", headers=auth_headers).json()
    assert detail["questions"][0]["follow_ups"] == [
        {
            "id": current["follow_up"]["id"],
            "question_id": current["question"]["id"],
            "position": 1,
            "question_text": "Who else was involved?",
            "answer_text": None,
        }
    ]


def test_other_users_cannot_answer_my_follow_up(
    client, auth_headers, other_auth_headers, start_interview, answer_current, question_generator
):
    interview = start_interview()
    question_generator.follow_ups = ["What changed afterwards?"]
    _, body = answer_current(interview)

    response = _answer_follow_up(
        client, other_auth_headers, interview["id"], interview["current_question"]["id"], body["follow_up"]["id"]
    )
    assert response.status_code == 404


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_follow_up_answers_are_rejected(client, auth_headers, start_interview, answer_current, question_generator, blank):
    interview = start_interview()
    question_generator.follow_ups = ["How did it end?"]
    _, body = answer_current(interview)

    response = _answer_follow_up(
        client, auth_headers, interview["id"], interview["current_question"]["id"], body["follow_up"]["id"], text=blank
    )
    assert response.status_code == 422
