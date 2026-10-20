# backend/app/routers/interviews.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion

router = APIRouter(prefix="/interviews", tags=["Interviews"])

@router.get("/{interview_id}/current-question")
def get_current_question(interview_id: int, db: Session = Depends(get_db)):
    # 1. Execute query and store result in a variable first
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    # 2. Check the variable (this evaluates safely and satisfies Pylance)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found."
        )
    
    interview_status = str(interview.status)
    if interview_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interview has already been completed."
        )
    
    current_question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_order == interview.current_question_position
        )
        .first()
    )
    
    if not current_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current question found for the specified position."
        )
        
    return {
        "interview_id": interview.id,
        "current_position": interview.current_question_position,
        "status": interview.status,
        "question": {
            "id": current_question.id,
            "text": current_question.question_text,
            "question_order": current_question.question_order
        }
    }