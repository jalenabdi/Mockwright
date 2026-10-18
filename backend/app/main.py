from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy.orm import Session
from .database import get_db
from pydantic import BaseModel
from .behave_questions import get_random_behavioral_question
from .models.answer import Answer
from .schemas.typed_answer import TypedAnswerInput, TypedAnswerReturn
from .models.interview_question import InterviewQuestion

app = FastAPI()


@app.get("/health")
def health_status():
    return {"status": "ok"}


class InterviewSettings(BaseModel):
    interview_type: str
    role: str


@app.post("/interviews/start")
def start_interview(settings: InterviewSettings):
    questions = get_random_behavioral_question()
    return {"questions": questions}

@app.post("/interviews/{interview_id}/answers", status_code=status.HTTP_201_CREATED)
def submit_answers(interview_id: int, payload: TypedAnswerInput, db: Session = Depends(get_db)):
    """" Endpoint to submit answers for a specific interview. """
    # Reject blank answers, questions that do not belong
    # to the interview, and duplicate submissions

    # The check for empty submissions is already handled by the Pydantic model validation in TypedAnswerInput.

    # Check if the question belongs to the interview
    question = db.query(InterviewQuestion).filter_by(id=payload.question_id, interview_id=interview_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The question does not belong to the specified interview.",
        )

    # Check for duplicate submissions
    existing_answer = db.query(Answer).filter_by(interview_question_id=payload.question_id).first()
    if existing_answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An answer for this question has already been submitted.",
        )

    # Create a new answer record if all checks pass
    new_answer = Answer(
        interview_question_id=payload.question_id,
        answer_text=payload.answer_text,    # Text is already stripped and validated by the Pydantic model
    )
    
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)

    return TypedAnswerReturn(
        id=new_answer.id,
        question_id=new_answer.interview_question_id,
        answer_text=new_answer.answer_text,
    )


    
    
