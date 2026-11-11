import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from .behave_questions import get_random_behavioral_question
from .database import get_db
from .dependencies import get_current_user
from .models import Interview, InterviewQuestion
from .models.user import User
from .schemas.auth import RegisterRequest
from .routers.auth import router as auth_router
from .routers.feedback import router as feedback_router
from .routers.interviews import router as interviews_router
from .schemas.interview import StartInterviewRequest
from .routers.voice import router as voice_router

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(auth_router)
app.include_router(interviews_router)
app.include_router(feedback_router)
app.include_router(voice_router)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "Unhandled API error for %s %s",
        request.method,
        request.url.path,
        exc_info=(type(error), error, error.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


@app.get("/health")
def health_status():
    return {"status": "ok"}


@app.post("/interviews/start", status_code=status.HTTP_201_CREATED)
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
        logger.exception("Could not save a new interview for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not start the interview. Please try again.",
        ) from None

    return response

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create an account from validated JSON credentials."""
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    password_hash = PasswordHash.recommended()
    db.add(
        User(
            email=payload.email,
            hashed_password=password_hash.hash(payload.password),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Could not create an account")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create the account. Please try again.",
        ) from None

    return {"message": "User registered successfully."}
    