from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.main import app
from backend.app.schemas.feedback import FeedbackReport, QuestionGrade
from backend.app.services.gemini_feedback import (
    FeedbackGenerationError,
    FeedbackUnavailableError,
    GeminiFeedbackGenerator,
    get_feedback_generator,
)
from backend.app.services.question_generator import InterviewContext, Turn

REPORT = FeedbackReport(
    relevance_score=18,
    star_structure_score=15,
    specificity_score=14,
    individual_contribution_score=17,
    communication_score=18,
    total_score=82,
    strengths=["You answered the question that was asked."],
    improvements=["Results were thin."],
    next_step="State one measurable result per answer.",
    question_grades=[
        QuestionGrade(question_number=n, score=60 + n, comment=f"Comment on answer {n}.") for n in range(1, 6)
    ],
)


class StubFeedbackGenerator:
    def __init__(self, result: Any = REPORT):
        self.result = result
        self.calls = []

    def generate(self, context, turns) -> FeedbackReport:
        self.calls.append((context, list(turns)))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def feedback_generator(client):
    generator = StubFeedbackGenerator()
    app.dependency_overrides[get_feedback_generator] = lambda: generator
    return generator


@pytest.fixture
def completed_interview(start_interview, answer_current):
    interview = start_interview()
    for n in range(1, 6):
        interview, _ = answer_current(interview, text=f"Answer number {n}")
    return interview


def test_feedback_is_refused_until_every_question_is_answered(client, auth_headers, start_interview, feedback_generator):
    interview = start_interview()
    response = client.post(f"/interviews/{interview['id']}/feedback", headers=auth_headers)
    assert response.status_code == 409
    assert feedback_generator.calls == []


def test_completed_interview_gets_one_saved_report(client, auth_headers, completed_interview, feedback_generator):
    url = f"/interviews/{completed_interview['id']}/feedback"

    created = client.post(url, headers=auth_headers)
    assert created.status_code == 201
    assert created.json()["total_score"] == 82

    _, turns = feedback_generator.calls[0]
    assert [t.answer for t in turns] == [f"Answer number {n}" for n in range(1, 6)]

    repeated = client.post(url, headers=auth_headers)
    assert repeated.status_code == 200
    assert repeated.json() == created.json()
    assert len(feedback_generator.calls) == 1

    assert client.get(url, headers=auth_headers).json() == created.json()


def test_saved_report_keeps_a_grade_for_each_question(client, auth_headers, completed_interview, feedback_generator):
    url = f"/interviews/{completed_interview['id']}/feedback"
    client.post(url, headers=auth_headers)

    grades = client.get(url, headers=auth_headers).json()["question_grades"]

    assert [(g["question_number"], g["score"], g["comment"]) for g in grades] == [
        (1, 61, "Comment on answer 1."),
        (2, 62, "Comment on answer 2."),
        (3, 63, "Comment on answer 3."),
        (4, 64, "Comment on answer 4."),
        (5, 65, "Comment on answer 5."),
    ]


def test_history_and_detail_show_the_saved_score(client, auth_headers, completed_interview, feedback_generator):
    client.post(f"/interviews/{completed_interview['id']}/feedback", headers=auth_headers)

    history = client.get("/interviews", headers=auth_headers).json()
    assert history[0]["total_score"] == 82
    detail = client.get(f"/interviews/{completed_interview['id']}", headers=auth_headers).json()
    assert detail["feedback"]["next_step"] == "State one measurable result per answer."


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [(FeedbackGenerationError("bad data"), 502), (FeedbackUnavailableError("no key"), 503)],
)
def test_generator_failure_gives_controlled_error_and_saves_nothing(
    client, auth_headers, completed_interview, feedback_generator, error, expected_status
):
    feedback_generator.result = error
    url = f"/interviews/{completed_interview['id']}/feedback"

    response = client.post(url, headers=auth_headers)

    assert response.status_code == expected_status
    assert "detail" in response.json()
    assert client.get(url, headers=auth_headers).status_code == 404


def test_other_users_cannot_read_or_create_my_feedback(client, other_auth_headers, completed_interview, feedback_generator):
    url = f"/interviews/{completed_interview['id']}/feedback"
    assert client.post(url, headers=other_auth_headers).status_code == 404
    assert client.get(url, headers=other_auth_headers).status_code == 404


class FakeGeminiModels:
    def __init__(self, parsed):
        self.parsed = parsed
        self.requests = []

    def generate_content(self, *, model, contents, config):
        self.requests.append(contents)
        return SimpleNamespace(parsed=self.parsed, text=None)


def _grade(number, score, comment):
    return SimpleNamespace(question_number=number, score=score, comment=comment)


def _scores(**overrides):
    values = dict(
        relevance_score=10,
        star_structure_score=11,
        specificity_score=12,
        individual_contribution_score=13,
        communication_score=14,
        strengths=["Clear"],
        improvements=["Add numbers"],
        next_step="Practice results.",
        question_grades=[_grade(1, 72, "Clear story, but no result.")],
    )
    values.update(overrides)
    return SimpleNamespace(**values)


CONTEXT = InterviewContext("Product Manager", "senior", None)
TURNS = [Turn("Tell me about a launch.", "I shipped checkout v2.")]


def test_gemini_feedback_computes_the_total_from_category_scores():
    models = FakeGeminiModels(_scores())
    generator = GeminiFeedbackGenerator(client=SimpleNamespace(models=models), model="m")

    report = generator.generate(CONTEXT, TURNS)

    assert report.total_score == 60
    assert "I shipped checkout v2." in models.requests[0]
    assert "Product Manager" in models.requests[0]


def test_gemini_feedback_rejects_out_of_range_scores():
    models = FakeGeminiModels(_scores(relevance_score=35))
    generator = GeminiFeedbackGenerator(client=SimpleNamespace(models=models), model="m")
    with pytest.raises(FeedbackGenerationError):
        generator.generate(CONTEXT, TURNS)


TWO_TURNS = [
    Turn("Tell me about a launch.", "I shipped checkout v2."),
    Turn("Tell me about a conflict.", "We disagreed."),
]


def test_gemini_feedback_grades_each_question_in_order():
    models = FakeGeminiModels(_scores(question_grades=[
        _grade(2, 40, "  Too short:   no  situation or result. "),
        _grade(1, 85, "Specific launch with your own decisions."),
    ]))
    generator = GeminiFeedbackGenerator(client=SimpleNamespace(models=models), model="m")

    report = generator.generate(CONTEXT, TWO_TURNS)

    assert [g.model_dump() for g in report.question_grades] == [
        {"question_number": 1, "score": 85, "comment": "Specific launch with your own decisions."},
        {"question_number": 2, "score": 40, "comment": "Too short: no situation or result."},
    ]


@pytest.mark.parametrize(
    "grades",
    [
        [_grade(1, 80, "Good.")],  # question 2 not graded
        [_grade(1, 80, "Good."), _grade(1, 70, "Again."), _grade(2, 50, "Thin.")],  # graded twice
        [_grade(1, 80, "Good."), _grade(2, 140, "Too high.")],  # out of range
    ],
)
def test_gemini_feedback_rejects_incomplete_or_invalid_question_grades(grades):
    models = FakeGeminiModels(_scores(question_grades=grades))
    generator = GeminiFeedbackGenerator(client=SimpleNamespace(models=models), model="m")
    with pytest.raises(FeedbackGenerationError):
        generator.generate(CONTEXT, TWO_TURNS)
