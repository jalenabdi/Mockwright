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


# --- Follow-ups -------------------------------------------------------------

from backend.app.services.question_generator import NextStep  # noqa: E402

ANSWERED = [Turn(question="Describe a hard query.", answer="We fixed it.")]


class StubStepGenerator(StubGenerator):
    def __init__(self, step: Any, question: Any = "Tell me about a launch you led."):
        super().__init__(question)
        self.step = step
        self.step_calls = []

    def next_step(self, context, history, *, can_follow_up, is_last):
        self.step_calls.append({"can_follow_up": can_follow_up, "is_last": is_last})
        if isinstance(self.step, Exception):
            raise self.step
        return self.step


def test_resilient_generator_keeps_a_good_follow_up():
    primary = StubStepGenerator(NextStep(follow_up="  What did you change yourself?  "))
    generator = ResilientQuestionGenerator(primary, QuestionBank())
    step = generator.next_step(CONTEXT, ANSWERED, can_follow_up=True, is_last=False)
    assert step == NextStep(follow_up="What did you change yourself?")


def test_resilient_generator_moves_on_with_the_bank_when_the_primary_fails():
    generator = ResilientQuestionGenerator(StubStepGenerator(RuntimeError("Gemini down")), QuestionBank())
    step = generator.next_step(CONTEXT, ANSWERED, can_follow_up=True, is_last=False)
    assert step.follow_up is None
    assert step.next_question in QuestionBank.QUESTIONS


def test_resilient_generator_ignores_a_follow_up_that_is_not_allowed():
    primary = StubStepGenerator(NextStep(follow_up="A third probe?"))
    generator = ResilientQuestionGenerator(primary, QuestionBank())
    step = generator.next_step(CONTEXT, ANSWERED, can_follow_up=False, is_last=True)
    assert step == NextStep()


@pytest.mark.parametrize("bad", [NextStep(), NextStep(next_question="Describe a hard query.")])
def test_resilient_generator_replaces_a_missing_or_repeated_next_question(bad):
    generator = ResilientQuestionGenerator(StubStepGenerator(bad), QuestionBank())
    step = generator.next_step(CONTEXT, ANSWERED, can_follow_up=True, is_last=False)
    assert step.next_question in QuestionBank.QUESTIONS


class FakeStepModels:
    def __init__(self, parsed):
        self.parsed = parsed
        self.requests = []

    def generate_content(self, *, model, contents, config):
        self.requests.append(contents)
        return SimpleNamespace(parsed=self.parsed, text=None)


def test_gemini_generator_can_ask_a_follow_up():
    models = FakeStepModels(SimpleNamespace(action="follow_up", follow_up=" Got it. What was the result? ", next_question=""))
    generator = GeminiQuestionGenerator(client=SimpleNamespace(models=models), model="test-model")

    step = generator.next_step(CONTEXT, ANSWERED, can_follow_up=True, is_last=False)

    assert step == NextStep(follow_up="Got it. What was the result?")
    assert '"follow_ups_left_for_this_question": true' in models.requests[0]


def test_gemini_generator_moves_on_with_the_next_question():
    models = FakeStepModels(SimpleNamespace(action="move_on", follow_up="", next_question="Tell me about a conflict."))
    generator = GeminiQuestionGenerator(client=SimpleNamespace(models=models), model="test-model")
    step = generator.next_step(CONTEXT, ANSWERED, can_follow_up=True, is_last=False)
    assert step == NextStep(next_question="Tell me about a conflict.")


def test_gemini_generator_skips_the_call_when_the_interview_is_over():
    models = FakeStepModels(None)
    generator = GeminiQuestionGenerator(client=SimpleNamespace(models=models), model="test-model")
    assert generator.next_step(CONTEXT, ANSWERED, can_follow_up=False, is_last=True) == NextStep()
    assert models.requests == []


# --- Hedging stalled calls --------------------------------------------------

import threading  # noqa: E402
import time  # noqa: E402


class StallOnceModels:
    """The first call hangs (like a stalled Gemini request); later calls answer at once."""

    def __init__(self):
        self.calls = 0
        self.release = threading.Event()
        self.lock = threading.Lock()

    def generate_content(self, *, model, contents, config):
        with self.lock:
            self.calls += 1
            number = self.calls
        if number == 1:
            self.release.wait(5)
            return SimpleNamespace(parsed=SimpleNamespace(question="Too late."), text=None)
        return SimpleNamespace(parsed=SimpleNamespace(question="The hedged question?"), text=None)


def test_a_stalled_gemini_call_is_hedged_with_a_second_one():
    models = StallOnceModels()
    generator = GeminiQuestionGenerator(client=SimpleNamespace(models=models), model="m", hedge_after=0.05)
    started = time.perf_counter()

    question = generator.next_question(CONTEXT, [])

    models.release.set()
    assert question == "The hedged question?"
    assert models.calls == 2
    assert time.perf_counter() - started < 2


def test_a_fast_gemini_call_is_not_hedged():
    models = FakeGeminiModels("Quick question?")
    generator = GeminiQuestionGenerator(client=SimpleNamespace(models=models), model="m", hedge_after=1)
    assert generator.next_question(CONTEXT, []) == "Quick question?"
    assert len(models.requests) == 1
