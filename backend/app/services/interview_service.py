"""Interview service: starts interviews, saves answers, decides what comes next.

This is the one place answers are written and progress advanced. It has no
dependency on FastAPI, so typed answers and voice transcripts share it.

An interview is five main questions. Each one is a short conversation: the
candidate answers, and the interviewer either asks a follow-up (at most
MAX_FOLLOW_UPS) or moves on. Saving an answer never moves the interview
forward by itself; `current_turn` does that, so a crash between the two can be
recovered by simply asking for the current turn again.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..models import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    Answer,
    FollowUp,
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
    MAX_FOLLOW_UPS,
    TOTAL_QUESTIONS,
    InterviewContext,
    QuestionGenerator,
    Turn,
)


@dataclass
class CurrentTurn:
    """What the candidate answers next: a main question, or a follow-up on it."""

    question: InterviewQuestion
    follow_up: FollowUp | None = None


def context_for(interview: Interview) -> InterviewContext:
    return InterviewContext(
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        job_description=interview.job_description,
    )


def answered_count(db: Session, interview_id: int) -> int:
    """How many main questions have an answer."""
    return db.scalar(
        select(func.count())
        .select_from(Answer)
        .join(InterviewQuestion, Answer.interview_question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview_id)
    ) or 0


def conversation_so_far(db: Session, interview_id: int) -> list[Turn]:
    """Every answered main question in order, with its answered follow-ups."""
    questions = db.scalars(
        select(InterviewQuestion)
        .join(Answer, Answer.interview_question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.question_order)
        .options(selectinload(InterviewQuestion.answer), selectinload(InterviewQuestion.follow_ups))
    ).all()
    return [
        Turn(
            question=q.question_text,
            answer=q.answer.answer_text if q.answer else "",
            follow_ups=tuple(
                Turn(question=f.question_text, answer=f.answer_text)
                for f in q.follow_ups
                if f.answer_text is not None
            ),
        )
        for q in questions
    ]


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
        select(InterviewQuestion)
        .where(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_order == order,
        )
        .options(selectinload(InterviewQuestion.answer), selectinload(InterviewQuestion.follow_ups))
        .execution_options(populate_existing=True)
    )


def current_turn(
    db: Session, interview: Interview, generator: QuestionGenerator
) -> CurrentTurn | None:
    """Return what the candidate answers next, deciding it first if needed.

    Returns None once the interview is completed. Safe to call repeatedly and
    concurrently: if two requests race to write the same question or
    follow-up, a unique rule keeps one and the loser re-reads it.
    """
    for _ in range(4):  # e.g. decide to move on -> write the next question -> return it
        db.refresh(interview)
        if interview.status == STATUS_COMPLETED:
            return None

        position = interview.current_question_position
        question = _question_at(db, interview.id, position)
        if question is None:
            _write_question(db, interview, position, generator)
            continue
        if question.answer is None:
            return CurrentTurn(question)
        open_follow_up = next((f for f in question.follow_ups if f.answer_text is None), None)
        if open_follow_up is not None:
            return CurrentTurn(question, open_follow_up)

        # The question and every follow-up are answered: follow up or move on.
        step = generator.next_step(
            context_for(interview),
            conversation_so_far(db, interview.id),
            can_follow_up=len(question.follow_ups) < MAX_FOLLOW_UPS,
            is_last=position >= TOTAL_QUESTIONS,
        )
        if step.follow_up:
            follow_up = FollowUp(
                interview_question_id=question.id,
                position=len(question.follow_ups) + 1,
                question_text=step.follow_up,
            )
            db.add(follow_up)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()  # another request asked one first; read that instead
                continue
            db.refresh(follow_up)
            return CurrentTurn(question, follow_up)
        _move_on(db, interview.id, position, step.next_question)
    raise RuntimeError(f"Interview {interview.id} did not settle on a current turn.")


def _write_question(db: Session, interview: Interview, position: int, generator: QuestionGenerator) -> None:
    text = generator.next_question(context_for(interview), conversation_so_far(db, interview.id))
    db.add(InterviewQuestion(interview_id=interview.id, question_order=position, question_text=text))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # written by a simultaneous request


def _move_on(db: Session, interview_id: int, position: int, next_question: str | None) -> None:
    """Close question `position`: complete the interview, or open the next question."""
    try:
        interview = db.execute(
            select(Interview).where(Interview.id == interview_id).with_for_update()
        ).scalar_one()
        if interview.status == STATUS_COMPLETED or interview.current_question_position != position:
            db.rollback()  # another request already moved on
            return
        interview.current_question_position = position + 1
        if position >= TOTAL_QUESTIONS:
            interview.status = STATUS_COMPLETED
        elif next_question:
            db.add(
                InterviewQuestion(
                    interview_id=interview_id, question_order=position + 1, question_text=next_question
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()


def _lock_open_interview(db: Session, interview_id: int) -> Interview:
    interview = db.execute(
        select(Interview).where(Interview.id == interview_id).with_for_update()
    ).scalar_one_or_none()
    if interview is None:
        raise InterviewNotFoundError(f"Interview {interview_id!r} was not found.")
    if interview.status == STATUS_COMPLETED:
        raise InterviewAlreadyCompletedError(f"Interview {interview_id!r} is already completed.")
    return interview


def _clean_answer(answer_text: str) -> str:
    stripped = answer_text.strip()
    if not stripped:
        raise BlankAnswerError("Answer text cannot be blank.")
    return stripped


def save_answer(db: Session, interview_id: int, question_id: int, answer_text: str) -> Answer:
    """Save the answer to the current main question.

    Runs as one transaction that locks the interview row (SELECT ... FOR
    UPDATE on Postgres) so two simultaneous submissions can't both save.
    Raises an InterviewServiceError subclass on invalid input or state.
    """
    text = _clean_answer(answer_text)
    try:
        interview = _lock_open_interview(db, interview_id)
        question = db.get(InterviewQuestion, question_id)
        if question is None or question.interview_id != interview_id:
            raise QuestionNotInInterviewError(
                f"Question {question_id!r} does not belong to interview {interview_id!r}."
            )
        if db.scalar(select(Answer.id).where(Answer.interview_question_id == question_id)):
            raise AnswerAlreadyExistsError(f"Question {question_id!r} already has an answer.")
        if question.question_order != interview.current_question_position:
            raise QuestionOutOfOrderError(f"Question {question_id!r} is not the current question.")

        answer = Answer(interview_question_id=question_id, answer_text=text)
        db.add(answer)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AnswerAlreadyExistsError(f"Question {question_id!r} already has an answer.") from None
    except Exception:
        db.rollback()
        raise
    db.refresh(answer)
    return answer


def save_follow_up_answer(
    db: Session, interview_id: int, question_id: int, follow_up_id: int, answer_text: str
) -> FollowUp:
    """Save the answer to the open follow-up on the current question."""
    text = _clean_answer(answer_text)
    try:
        interview = _lock_open_interview(db, interview_id)
        follow_up = db.get(FollowUp, follow_up_id)
        question = db.get(InterviewQuestion, question_id)
        if (
            follow_up is None
            or question is None
            or question.interview_id != interview_id
            or follow_up.interview_question_id != question_id
        ):
            raise QuestionNotInInterviewError(
                f"Follow-up {follow_up_id!r} does not belong to interview {interview_id!r}."
            )
        if follow_up.answer_text is not None:
            raise AnswerAlreadyExistsError(f"Follow-up {follow_up_id!r} already has an answer.")
        if question.question_order != interview.current_question_position:
            raise QuestionOutOfOrderError(f"Follow-up {follow_up_id!r} is not on the current question.")

        follow_up.answer_text = text
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(follow_up)
    return follow_up
