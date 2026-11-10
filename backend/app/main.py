from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from .behave_questions import get_random_behavioral_question
from .database import get_db
from .dependencies import get_current_user
from .models import Interview, InterviewQuestion
from .models.user import User
from .routers.auth import router as auth_router
from .routers.feedback import router as feedback_router
from .routers.interviews import router as interviews_router
from .schemas.interview import StartInterviewRequest
from .routers.voice import router as voice_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(interviews_router)
app.include_router(feedback_router)
app.include_router(voice_router)


@app.get("/health")
def health_status():
    return {"status": "ok"}


@app.post("/interviews/start", status_code=201)
def start_interview(
    settings: StartInterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    selected_questions = get_random_behavioral_question(count=5)

    try:
        interview = Interview(
            user_id=current_user.id,
            target_role=settings.target_role,
            experience_level=settings.experience_level.value,
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

@app.post("/auth/register", status_code=201)
def register_user(email: str, password: str, db: Session = Depends(get_db)):
    # Validate input, reject duplicate emails, hash passwords with pwdlib and Argon2 before saving
    if not email or not password:   # Validation for empty email or password
        raise HTTPException(status_code=400, detail="Email and password are required.")

    #####    ENSURE EMAIL AND PASSWORD FIT THE USER SCHEMA REQUIREMENTS                #####
    #####   IMPORT USER MODEL WHENEVER IT IS FINISHED   #####
    if db.query(User).filter(User.email == email).first():  # Check for duplicate email
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Hash the password using pwd/Argon2
    password_hash = PasswordHash()
    hashed_password = password_hash.hash(password)
    db.add(User(email=email, hashed_password=hashed_password))
    db.commit()
    return {"message": "User registered successfully."}
    