# backend/app/routers/interviews.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.schemas.typed_answer import TypedAnswerInput, TypedAnswerReturn

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.get("/{interview_id}/current-question")
def get_current_question(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )

    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interview has already been completed.",
        )

    current_question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_order == interview.current_question_position,
        )
        .first()
    )

    if not current_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current question found for the specified position.",
        )

    return {
        "interview_id": interview.id,
        "current_position": interview.current_question_position,
        "status": interview.status,
        "question": {
            "id": current_question.id,
            "text": current_question.question_text,
            "question_order": current_question.question_order,
        },
    }


@router.post("/{interview_id}/answers", status_code=status.HTTP_201_CREATED)
def submit_answer(
    interview_id: int,
    payload: TypedAnswerInput,
    db: Session = Depends(get_db),
):
    """Submit a typed answer for the current question in an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )

    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview has already been completed.",
        )

    question = (
        db.query(InterviewQuestion)
        .filter_by(id=payload.question_id, interview_id=interview_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The question does not belong to the specified interview.",
        )

    if question.question_order != interview.current_question_position:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This question is not the current question for the interview.",
        )

    existing_answer = (
        db.query(Answer).filter_by(interview_question_id=payload.question_id).first()
    )
    if existing_answer:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An answer for this question has already been submitted.",
        )

    new_answer = Answer(
        interview_question_id=payload.question_id,
        answer_text=payload.answer_text,
    )
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)

    total_questions = (
        db.query(InterviewQuestion).filter_by(interview_id=interview_id).count()
    )
    interview.current_question_position += 1
    if interview.current_question_position > total_questions:
        interview.status = "completed"
    db.commit()

    return TypedAnswerReturn(
        id=new_answer.id,
        question_id=new_answer.interview_question_id,
        answer_text=new_answer.answer_text,
    )
