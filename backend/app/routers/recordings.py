"""Answer videos: upload one per question, play it back later.

The browser sends the video as the raw request body with its MIME type as the
Content-Type, e.g. `video/webm;codecs=vp9,opus`. Only the interview's owner
can upload or watch; anyone else gets the same 404 as a missing interview.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import DbSession, OwnedInterview
from ..models import Interview, InterviewQuestion, Recording
from ..services.recording_store import (
    EXTENSIONS,
    EmptyRecordingError,
    RecordingStore,
    RecordingTooLargeError,
    base_mime_type,
    get_recording_store,
)

router = APIRouter(prefix="/interviews", tags=["Recordings"])

Store = Annotated[RecordingStore, Depends(get_recording_store)]


class RecordingOut(BaseModel):
    question_id: int
    mime_type: str
    size_bytes: int
    duration_seconds: float | None


def _question_in(db: Session, interview: Interview, question_id: int) -> InterviewQuestion:
    question = db.get(InterviewQuestion, question_id)
    if question is None or question.interview_id != interview.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    return question


@router.put("/{interview_id}/questions/{question_id}/recording", response_model=RecordingOut)
async def upload_recording(
    request: Request,
    interview: OwnedInterview,
    question_id: int,
    db: DbSession,
    store: Store,
    duration_seconds: Annotated[float | None, Query(ge=0, le=3600)] = None,
) -> RecordingOut:
    """Save the video of this answer, replacing any earlier one."""
    mime_type = base_mime_type(request.headers.get("content-type"))
    if mime_type not in EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Recordings must be WebM or MP4 video.",
        )
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > store.max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Recording is too large.")

    question = _question_in(db, interview, question_id)
    relative = store.relative_path(interview.user_id, interview.id, question.question_order, mime_type)
    try:
        size = await store.save(relative, request.stream())
    except RecordingTooLargeError:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Recording is too large.")
    except EmptyRecordingError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Recording is empty.")

    recording = question.recording
    if recording is None:
        recording = Recording(interview_question_id=question.id, file_name=relative)
        db.add(recording)
    elif recording.file_name != relative:
        store.delete(recording.file_name)  # format changed, e.g. webm -> mp4
    recording.file_name = relative
    recording.mime_type = mime_type
    recording.size_bytes = size
    recording.duration_seconds = duration_seconds
    db.commit()

    return RecordingOut(
        question_id=question.id,
        mime_type=mime_type,
        size_bytes=size,
        duration_seconds=duration_seconds,
    )


@router.get("/{interview_id}/questions/{question_id}/recording")
def get_recording(
    interview: OwnedInterview, question_id: int, db: DbSession, store: Store
) -> FileResponse:
    """Stream the saved video of this answer."""
    question = _question_in(db, interview, question_id)
    recording = question.recording
    path = store.path_for(recording.file_name) if recording else None
    if recording is None or path is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recording for this question.")
    return FileResponse(path, media_type=recording.mime_type)
