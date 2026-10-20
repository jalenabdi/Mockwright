from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .behave_questions import get_random_behavioral_question
from .database import get_db
from .models import Answer, Interview, InterviewQuestion
from .schemas.interview import StartInterviewRequest

app = FastAPI()
app.include_router(interviews_router)


@app.get("/health")
def health_status():
    return {"status": "ok"}


@app.post("/interviews/start", status_code=201)
def start_interview(settings: StartInterviewRequest, db: Session = Depends(get_db)):
    selected_questions = get_random_behavioral_question(count=5)

    try:
        interview = Interview(
            target_role=settings.target_role,
            experience_level=settings.experience_level,
            job_description=settings.job_description,
            status="in_progress",
            current_question_position=1,
        )
        db.add(interview)
        db.flush()

        question_rows = [
            InterviewQuestion(
                interview_id=interview.id,
                question_order=order,
                question_text=text,
            )
            for order, text in enumerate(selected_questions, start=1)
        ]
        db.add_all(question_rows)
        db.flush()

        response = {
            "interview_id": interview.id,
            "questions": [
                {
                    "id": row.id,
                    "question_order": row.question_order,
                    "question_text": row.question_text,
                }
                for row in question_rows
            ],
        }

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not start the interview.")

    return response


@app.get("/interviews/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found.")

    total_question_count = db.scalar(
        select(func.count(InterviewQuestion.id)).where(
            InterviewQuestion.interview_id == interview.id
        )
    )
    answered_count = db.scalar(
        select(func.count(Answer.id))
        .join(InterviewQuestion, Answer.interview_question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview.id)
    )

    current_question_number = (
        None if interview.status == "completed" else interview.current_question_position
    )

    return {
        "interview_id": interview.id,
        "status": interview.status,
        "answered_count": answered_count,
        "total_question_count": total_question_count,
        "current_question_number": current_question_number,
    }
