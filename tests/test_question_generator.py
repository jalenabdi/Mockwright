from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.services.question_generator import (
    GeminiQuestionGenerator,
    InterviewContext,
    QuestionBank,
    ResilientQuestionGenerator,
    Turn,
)

CONTEXT = InterviewContext(
    target_role="Data Analyst",
    experience_level="junior",
    job_description="SQL dashboards for the finance team.",
)


class StubGenerator:
    def __init__(self, result: Any):
        self.result = result
        self.calls = []

    def next_question(self, context, history) -> str:
        self.calls.append((context, list(history)))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_bank_never_repeats_a_question_already_asked():
    bank = QuestionBank()
    history: list[Turn] = []
    for _ in range(5):
        question = bank.next_question(CONTEXT, history)
        history.append(Turn(question=question, answer="An answer."))
    assert len({turn.question for turn in history}) == 5


def test_resilient_generator_uses_the_primary_question():
    primary = StubGenerator("Tell me about a dashboard that changed a decision.")
    generator = ResilientQuestionGenerator(primary, QuestionBank())
    assert generator.next_question(CONTEXT, []) == "Tell me about a dashboard that changed a decision."


def test_resilient_generator_falls_back_when_primary_fails():
    generator = ResilientQuestionGenerator(StubGenerator(RuntimeError("Gemini down")), QuestionBank())
    question = generator.next_question(CONTEXT, [])
    assert question in QuestionBank.QUESTIONS


@pytest.mark.parametrize("bad", ["", "   ", "Tell me about yourself."])
def test_resilient_generator_falls_back_on_blank_or_repeated_question(bad):
    history = [Turn(question="Tell me about yourself.", answer="I like data.")]
    generator = ResilientQuestionGenerator(StubGenerator(bad), QuestionBank())
    question = generator.next_question(CONTEXT, history)
    assert question.strip()
    assert question != "Tell me about yourself."


class FakeGeminiModels:
    def __init__(self, question):
        self.question = question
        self.requests = []

    def generate_content(self, *, model, contents, config):
        self.requests.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(parsed=SimpleNamespace(question=self.question), text=None)


def test_gemini_generator_sends_settings_and_previous_answers_to_the_model():
    models = FakeGeminiModels("  What did the finance team do with that dashboard?  ")
    generator = GeminiQuestionGenerator(client=SimpleNamespace(models=models), model="test-model")
    history = [Turn(question="Describe a hard query.", answer="I rewrote a 40-table join.")]

    question = generator.next_question(CONTEXT, history)

    assert question == "What did the finance team do with that dashboard?"
    prompt = models.requests[0]["contents"]
    for expected in ["Data Analyst", "junior", "SQL dashboards", "Describe a hard query.", "40-table join"]:
        assert expected in prompt
    assert models.requests[0]["model"] == "test-model"
