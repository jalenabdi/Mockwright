"""Interview service: saves an answer and advances interview progress.

This is the one place an answer gets written and an interview's progress
advanced. It has no dependency on HTTP or FastAPI, so the same function can
be called from a REST route today and from a voice transcript pipeline in
Week 6 without changes.

--- Assumed Interview model contract ---
The Interview model lives on a separate, not-yet-merged branch. This module
is written against the following contract so it can be built and tested on
its own; see the PR description for the full note to reviewers.

    from backend.app.models.interview import Interview

    Interview.status                  : str   # STATUS_IN_PROGRESS | STATUS_COMPLETED
    Interview.current_question_index  : int   # 0-based; equals the number of
                                               # answered questions. The current
                                               # question has
                                               # question_order == current_question_index + 1.
    Interview.updated_at              : datetime  # set by this service on every save

The primary key type (int vs UUID) is undecided, so interview_id is typed
loosely (uuid.UUID | int) and only ever compared with plain equality, never
assumed to be an Integer column.

Interview.questions is NOT assumed to exist as a relationship. Questions are
loaded with an explicit select() on InterviewQuestion filtered by
interview_id instead.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.answer import Answer
from backend.app.models.interview import Interview
from backend.app.models.interview_question import InterviewQuestion

from .exceptions import (
    AnswerAlreadyExistsError,
    BlankAnswerError,
    InterviewAlreadyCompletedError,
    InterviewNotFoundError,
    QuestionNotInInterviewError,
    QuestionOutOfOrderError,
)

# Allowed values of Interview.status. Defined as constants here (rather than
# imported from an enum on the model) so there's one place to change if the
# model later switches to a real enum type.
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"

InterviewId = uuid.UUID | int


@dataclass
class AnswerResult:
    """Outcome of save_answer, enough for a route to build its response."""

    answer: Answer
    status: str
    answered_count: int
    total_questions: int
    next_question: InterviewQuestion | None


def save_answer(
    db: Session,
    interview_id: InterviewId,
    question_id: int,
    answer_text: str,
) -> AnswerResult:
    """Save an answer to an interview question and advance progress.

    Runs as one transaction: locks the interview row (SELECT ... FOR UPDATE)
    so two simultaneous submissions for the same interview can't both
    advance progress, validates the question and current position, saves
    the answer, advances current_question_index by one, and marks the
    interview completed once every one of its questions has an answer.

    Blank-text input is rejected before any database work, so bad input
    never takes out the row lock.

    Raises one of the InterviewServiceError subclasses in exceptions.py on
    any invalid input or state. Commits on success; rolls back and
    re-raises on any failure, including converting a unique-constraint
    race on the answer into AnswerAlreadyExistsError instead of letting the
    IntegrityError propagate.
    """
    stripped_text = answer_text.strip()
    if not stripped_text:
        raise BlankAnswerError("Answer text cannot be blank.")

    try:
        interview = db.get(Interview, interview_id, with_for_update=True)
        if interview is None:
            raise InterviewNotFoundError(f"Interview {interview_id!r} was not found.")

        if interview.status == STATUS_COMPLETED:
            raise InterviewAlreadyCompletedError(
                f"Interview {interview_id!r} is already completed."
            )

        question = db.get(InterviewQuestion, question_id)
        if question is None or question.interview_id != interview_id:
            raise QuestionNotInInterviewError(
                f"Question {question_id!r} does not belong to interview {interview_id!r}."
            )

        existing_answer = db.scalar(
            select(Answer).where(Answer.interview_question_id == question_id)
        )
        if existing_answer is not None:
            raise AnswerAlreadyExistsError(f"Question {question_id!r} already has an answer.")

        current_order = interview.current_question_index + 1
        if question.question_order != current_order:
            raise QuestionOutOfOrderError(
                f"Question {question_id!r} has order {question.question_order}, "
                f"but the current question order is {current_order}."
            )

        answer = Answer(interview_question_id=question_id, answer_text=stripped_text)
        db.add(answer)
        db.flush()

        interview.current_question_index += 1

        total_questions = (
            db.scalar(
                select(func.count())
                .select_from(InterviewQuestion)
                .where(InterviewQuestion.interview_id == interview_id)
            )
            or 0
        )
        answered_count = (
            db.scalar(
                select(func.count())
                .select_from(Answer)
                .join(InterviewQuestion, Answer.interview_question_id == InterviewQuestion.id)
                .where(InterviewQuestion.interview_id == interview_id)
            )
            or 0
        )

        if answered_count >= total_questions:
            interview.status = STATUS_COMPLETED

        interview.updated_at = datetime.now(timezone.utc)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise AnswerAlreadyExistsError(f"Question {question_id!r} already has an answer.") from None
    except Exception:
        db.rollback()
        raise

    db.refresh(answer)
    db.refresh(interview)

    next_question = None
    if interview.status != STATUS_COMPLETED:
        next_question = db.scalar(
            select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview_id)
            .where(InterviewQuestion.question_order == interview.current_question_index + 1)
        )

    return AnswerResult(
        answer=answer,
        status=interview.status,
        answered_count=answered_count,
        total_questions=total_questions,
        next_question=next_question,
    )
