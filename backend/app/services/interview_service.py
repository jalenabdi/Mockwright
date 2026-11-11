"""Interview service: starts interviews, saves answers, writes the next question.

This is the one place answers are written and progress advanced. It has no
dependency on FastAPI, so typed answers and voice transcripts share it.

Questions are created one at a time: an interview starts with question 1, and
each saved answer (before the last) is followed by a newly generated question
that can build on everything the candidate has said.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    Answer,
    Interview,
    InterviewQuestion,
)
from .exceptions import (
    AnswerAlreadyExistsError,
    BlankAnswerError,
    InterviewAlreadyCompletedError,
    InterviewNotFoundError,
    QuestionNotInInterviewError,
    QuestionOutOfOrderError,
)
from .question_generator import (
    TOTAL_QUESTIONS,
    InterviewContext,
    QuestionGenerator,
    Turn,
)


@dataclass
class AnswerResult:
    """Outcome of save_answer, enough for a route to build its response."""

    answer: Answer
    status: str
    answered_count: int
    total_questions: int


def context_for(interview: Interview) -> InterviewContext:
    return InterviewContext(
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        job_description=interview.job_description,
    )


def answered_count(db: Session, interview_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Answer)
        .join(InterviewQuestion, Answer.interview_question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview_id)
    ) or 0


def conversation_so_far(db: Session, interview_id: int) -> list[Turn]:
    rows = db.execute(
        select(InterviewQuestion.question_text, Answer.answer_text)
        .join(Answer, Answer.interview_question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.question_order)
    ).all()
    return [Turn(question=q, answer=a) for q, a in rows]


def start_interview(
    db: Session,
    *,
    user_id: int,
    context: InterviewContext,
    generator: QuestionGenerator,
) -> Interview:
    """Create an interview and its first question in one transaction."""
    first_question = generator.next_question(context, [])

    interview = Interview(
        user_id=user_id,
        target_role=context.target_role,
        experience_level=context.experience_level,
        job_description=context.job_description,
        status=STATUS_IN_PROGRESS,
        current_question_position=1,
    )
    interview.questions.append(InterviewQuestion(question_order=1, question_text=first_question))
    db.add(interview)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(interview)
    return interview


def _question_at(db: Session, interview_id: int, order: int) -> InterviewQuestion | None:
    return db.scalar(
        select(InterviewQuestion).where(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_order == order,
        )
    )


def ensure_current_question(
    db: Session, interview: Interview, generator: QuestionGenerator
) -> InterviewQuestion | None:
    """Return the question being answered, writing it first if needed.

    Returns None once the interview is completed. Safe to call repeatedly and
    concurrently: if two requests race to write the same question, the
    unique (interview_id, question_order) rule keeps one and the loser re-reads it.
    """
    if interview.status == STATUS_COMPLETED:
        return None

    position = interview.current_question_position
    existing = _question_at(db, interview.id, position)
    if existing is not None:
        return existing

    history = conversation_so_far(db, interview.id)
    question_text = generator.next_question(context_for(interview), history)
    question = InterviewQuestion(
        interview_id=interview.id, question_order=position, question_text=question_text
    )
    db.add(question)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _question_at(db, interview.id, position)
    db.refresh(question)
    return question


def save_answer(
    db: Session,
    interview_id: int,
    question_id: int,
    answer_text: str,
) -> AnswerResult:
    """Save an answer to the current question and advance progress.

    Runs as one transaction that locks the interview row (SELECT ... FOR
    UPDATE on Postgres) so two simultaneous submissions can't both advance.
    Marks the interview completed after the final answer. Raises an
    InterviewServiceError subclass on invalid input or state.
    """
    stripped_text = answer_text.strip()
    if not stripped_text:
        raise BlankAnswerError("Answer text cannot be blank.")

    try:
        interview = db.execute(
            select(Interview).where(Interview.id == interview_id).with_for_update()
        ).scalar_one_or_none()
        if interview is None:
            raise InterviewNotFoundError(f"Interview {interview_id!r} was not found.")
        if interview.status == STATUS_COMPLETED:
            raise InterviewAlreadyCompletedError(f"Interview {interview_id!r} is already completed.")

        question = db.get(InterviewQuestion, question_id)
        if question is None or question.interview_id != interview_id:
            raise QuestionNotInInterviewError(
                f"Question {question_id!r} does not belong to interview {interview_id!r}."
            )

        if db.scalar(select(Answer.id).where(Answer.interview_question_id == question_id)):
            raise AnswerAlreadyExistsError(f"Question {question_id!r} already has an answer.")

        if question.question_order != interview.current_question_position:
            raise QuestionOutOfOrderError(
                f"Question {question_id!r} is not the current question."
            )

        answer = Answer(interview_question_id=question_id, answer_text=stripped_text)
        db.add(answer)
        db.flush()

        count = answered_count(db, interview_id)
        interview.current_question_position = count + 1
        if count >= TOTAL_QUESTIONS:
            interview.status = STATUS_COMPLETED

        db.commit()
    except IntegrityError:
        db.rollback()
        raise AnswerAlreadyExistsError(f"Question {question_id!r} already has an answer.") from None
    except Exception:
        db.rollback()
        raise

    db.refresh(answer)
    return AnswerResult(
        answer=answer,
        status=interview.status,
        answered_count=count,
        total_questions=TOTAL_QUESTIONS,
    )
