"""The signed-in user's resume: upload (replaces any earlier one), view, remove.

The browser sends the file as the raw request body, with its name in the
`file_name` query parameter. Only the extracted text is stored.
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..dependencies import CurrentUser, DbSession
from ..models import Resume
from ..services.resume_parser import (
    MAX_RESUME_BYTES,
    ResumeParseError,
    UnsupportedResumeError,
    extract_resume_text,
)

router = APIRouter(prefix="/resume", tags=["Resume"])

PREVIEW_CHARS = 280


class ResumeOut(BaseModel):
    file_name: str
    updated_at: datetime
    word_count: int
    # The start of the text we read, so the user can check it parsed correctly.
    preview: str

    @field_validator("updated_at")
    @classmethod
    def assume_utc(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _out(resume: Resume) -> ResumeOut:
    return ResumeOut(
        file_name=resume.file_name,
        updated_at=resume.updated_at,
        word_count=len(resume.text.split()),
        preview=resume.text[:PREVIEW_CHARS],
    )


def _mine(db: DbSession, user_id: int) -> Resume | None:
    return db.scalar(select(Resume).where(Resume.user_id == user_id))


@router.get("", response_model=ResumeOut)
def get_resume(current_user: CurrentUser, db: DbSession) -> ResumeOut:
    resume = _mine(db, current_user.id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No resume saved yet.")
    return _out(resume)


@router.put("", response_model=ResumeOut)
async def upload_resume(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    file_name: Annotated[str, Query(min_length=1, max_length=255)],
) -> ResumeOut:
    """Read the resume's text and save it to the account, replacing any earlier one."""
    too_large = HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Resumes can be up to 5 MB.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_RESUME_BYTES:
        raise too_large
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_RESUME_BYTES:
            raise too_large

    try:
        text = extract_resume_text(bytes(data), file_name)
    except UnsupportedResumeError as error:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(error))
    except ResumeParseError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))

    for _ in range(2):  # a simultaneous first upload can win the insert; then update it
        resume = _mine(db, current_user.id)
        if resume is None:
            resume = Resume(user_id=current_user.id, file_name=file_name, text=text)
            db.add(resume)
        else:
            resume.file_name = file_name
            resume.text = text
            resume.updated_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(resume)
        return _out(resume)
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Your resume was being saved twice. Try again.")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(current_user: CurrentUser, db: DbSession) -> Response:
    resume = _mine(db, current_user.id)
    if resume is not None:
        db.delete(resume)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
