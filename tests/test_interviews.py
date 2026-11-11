def test_start_creates_interview_with_only_the_first_question(start_interview, question_generator):
    interview = start_interview()

    assert interview["status"] == "in_progress"
    assert interview["total_questions"] == 5
    assert interview["answered_count"] == 0
    assert interview["current_question"]["question_order"] == 1
    assert interview["current_question"]["question_text"] == "Question 1 for Software Engineer?"
    assert len(interview["questions"]) == 1

    context, history = question_generator.calls[0]
    assert context.experience_level == "intern"
    assert context.job_description == "Build internal tools in Python."
    assert history == []


def test_start_rejects_unknown_experience_level(client, auth_headers, question_generator):
    response = client.post(
        "/interviews/start",
        json={"target_role": "PM", "experience_level": "wizard"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_start_requires_sign_in(client, question_generator):
    response = client.post("/interviews/start", json={"target_role": "PM", "experience_level": "senior"})
    assert response.status_code == 401


def test_next_question_is_generated_from_the_previous_answers(start_interview, answer_current, question_generator):
    interview = start_interview()
    interview, body = answer_current(interview, text="I led the API redesign.")

    assert body["answered_count"] == 1
    assert body["next_question"]["question_order"] == 2
    assert body["next_question"]["question_text"] == "Question 2 for Software Engineer?"

    _, history = question_generator.calls[-1]
    assert [(t.question, t.answer) for t in history] == [
        ("Question 1 for Software Engineer?", "I led the API redesign.")
    ]


def test_fifth_answer_completes_the_interview(start_interview, answer_current, question_generator):
    interview = start_interview()
    for _ in range(4):
        interview, body = answer_current(interview)
        assert body["status"] == "in_progress"

    interview, body = answer_current(interview)

    assert body["status"] == "completed"
    assert body["answered_count"] == 5
    assert body["next_question"] is None
    assert len(question_generator.calls) == 5  # no sixth question is written


def test_answer_is_rejected_when_blank_duplicate_or_not_current(client, auth_headers, start_interview, answer_current):
    interview = start_interview()
    url = f"/interviews/{interview['id']}/answers"
    first_id = interview["current_question"]["id"]

    blank = client.post(url, json={"question_id": first_id, "answer_text": "   "}, headers=auth_headers)
    assert blank.status_code == 422

    answer_current(interview)
    duplicate = client.post(url, json={"question_id": first_id, "answer_text": "Again"}, headers=auth_headers)
    assert duplicate.status_code == 409

    unknown = client.post(url, json={"question_id": 999_999, "answer_text": "Hi"}, headers=auth_headers)
    assert unknown.status_code == 400


def test_completed_interview_rejects_more_answers(client, auth_headers, start_interview, answer_current):
    interview = start_interview()
    first_id = interview["current_question"]["id"]
    for _ in range(5):
        interview, _ = answer_current(interview)

    response = client.post(
        f"/interviews/{interview['id']}/answers",
        json={"question_id": first_id, "answer_text": "One more"},
        headers=auth_headers,
    )
    assert response.status_code == 409

    current = client.get(f"/interviews/{interview['id']}/current-question", headers=auth_headers)
    assert current.status_code == 409


def test_progress_survives_a_refresh(client, auth_headers, start_interview, answer_current):
    interview = start_interview()
    interview, _ = answer_current(interview)
    interview, _ = answer_current(interview)

    current = client.get(f"/interviews/{interview['id']}/current-question", headers=auth_headers).json()
    assert current["question"]["question_order"] == 3
    assert current["question"]["id"] == interview["current_question"]["id"]
    assert current["total_questions"] == 5


def test_interview_detail_includes_questions_and_answers(client, auth_headers, start_interview, answer_current):
    interview = start_interview()
    interview, _ = answer_current(interview, text="First answer")

    detail = client.get(f"/interviews/{interview['id']}", headers=auth_headers).json()

    assert detail["target_role"] == "Software Engineer"
    assert detail["answered_count"] == 1
    assert [q["question_order"] for q in detail["questions"]] == [1, 2]
    assert detail["questions"][0]["answer_text"] == "First answer"
    assert detail["questions"][1]["answer_text"] is None
    assert detail["feedback"] is None


def test_history_lists_only_my_interviews_newest_first(client, auth_headers, other_auth_headers, start_interview):
    first = start_interview(target_role="Data Analyst")
    second = start_interview(target_role="Product Manager")
    start_interview(headers=other_auth_headers, target_role="Someone Else")

    history = client.get("/interviews", headers=auth_headers).json()

    assert [item["id"] for item in history] == [second["id"], first["id"]]
    assert history[0]["target_role"] == "Product Manager"
    assert history[0]["total_score"] is None
    assert history[0]["answered_count"] == 0


def test_other_users_cannot_see_or_answer_my_interview(client, other_auth_headers, start_interview):
    interview = start_interview()
    base = f"/interviews/{interview['id']}"

    assert client.get(base, headers=other_auth_headers).status_code == 404
    assert client.get(f"{base}/current-question", headers=other_auth_headers).status_code == 404
    answer = client.post(
        f"{base}/answers",
        json={"question_id": interview["current_question"]["id"], "answer_text": "Sneaky"},
        headers=other_auth_headers,
    )
    assert answer.status_code == 404
