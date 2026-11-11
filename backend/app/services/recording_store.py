"""Answer videos on disk.

Videos are saved as <recordings_dir>/<user_id>/<interview_id>/q<order>.<ext>.
The database keeps only the relative path (models/recording.py), so moving
storage somewhere else later (Cloudflare R2, say) means replacing this module.
"""
from __future__ import annotations

import os
import shutil
import uuid
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from ..config import get_settings

# A 3-minute answer at the browser's recording bitrate is ~15 MB; this leaves room.
MAX_RECORDING_BYTES = 60 * 1024 * 1024

# Browser recording formats we accept, and the file extension each is saved with.
EXTENSIONS = {"video/webm": "webm", "video/mp4": "mp4"}


class RecordingTooLargeError(ValueError):
    """The upload went past MAX_RECORDING_BYTES."""


class EmptyRecordingError(ValueError):
    """The upload had no bytes."""


def base_mime_type(content_type: str | None) -> str:
    """'video/webm;codecs=vp9,opus' -> 'video/webm'."""
    return (content_type or "").split(";", 1)[0].strip().lower()


class RecordingStore:
    def __init__(self, root: Path, max_bytes: int = MAX_RECORDING_BYTES):
        self.root = root
        self.max_bytes = max_bytes

    def relative_path(self, user_id: int, interview_id: int, order: int, mime_type: str) -> str:
        return f"{user_id}/{interview_id}/q{order}.{EXTENSIONS[mime_type]}"

    def path_for(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Recording path is outside the recordings folder.")
        return path

    async def save(self, relative: str, chunks: AsyncIterator[bytes]) -> int:
        """Write the upload to a temp file, then move it into place. Returns its size.

        A half-finished or oversized upload never replaces an existing video.
        """
        final = self.path_for(relative)
        final.parent.mkdir(parents=True, exist_ok=True)
        temp = final.with_name(f".{final.name}.{uuid.uuid4().hex}.part")
        size = 0
        try:
            with temp.open("wb") as file:
                async for chunk in chunks:
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise RecordingTooLargeError(f"Recording is over {self.max_bytes} bytes.")
                    file.write(chunk)
            if size == 0:
                raise EmptyRecordingError("Recording is empty.")
            os.replace(temp, final)
        finally:
            temp.unlink(missing_ok=True)
        return size

    def delete(self, relative: str) -> None:
        self.path_for(relative).unlink(missing_ok=True)

    def delete_interview(self, user_id: int, interview_id: int) -> None:
        shutil.rmtree(self.path_for(f"{user_id}/{interview_id}"), ignore_errors=True)


@lru_cache
def get_recording_store() -> RecordingStore:
    return RecordingStore(get_settings().recordings_dir)
