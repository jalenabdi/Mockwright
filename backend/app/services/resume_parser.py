"""Turns an uploaded resume (PDF, DOCX or plain text) into plain text.

Only the text is kept: it's what the interviewer reads to tailor questions.
Scanned resumes (images of text) have no text to read and are rejected with a
message saying so, rather than silently producing generic questions.
"""
from __future__ import annotations

import io
import logging
import re
import zipfile
from pathlib import PurePath
from xml.etree import ElementTree

from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_RESUME_CHARS = 20_000
MAX_PDF_PAGES = 10

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ResumeParseError(ValueError):
    """The file can't be read as a resume. The message is safe to show the user."""


class UnsupportedResumeError(ResumeParseError):
    """Not a PDF, DOCX or text file."""


def _clean(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.replace("\r", "\n").split("\n")]
    joined = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return joined[:MAX_RESUME_CHARS].strip()


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            reader.decrypt("")  # many "protected" resumes only restrict editing
        return "\n".join(page.extract_text() or "" for page in reader.pages[:MAX_PDF_PAGES])
    except Exception as error:  # pypdf raises many kinds of errors on bad files
        logger.info("Could not read PDF resume: %s", type(error).__name__)
        raise ResumeParseError("That PDF couldn't be opened. Try exporting it again, or upload a DOCX.") from error


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise ResumeParseError("That Word file couldn't be opened. Try saving it again, or upload a PDF.") from error
    paragraphs = []
    for paragraph in root.iter(f"{_WORD_NS}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{_WORD_NS}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{_WORD_NS}tab":
                parts.append(" ")
        paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


def extract_resume_text(data: bytes, file_name: str) -> str:
    """Return the resume's text, or raise ResumeParseError with a user-facing message."""
    extension = PurePath(file_name.lower()).suffix
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedResumeError("Upload your resume as a PDF, Word (.docx) or text file.")

    if extension == ".pdf":
        raw = _pdf_text(data)
    elif extension == ".docx":
        raw = _docx_text(data)
    else:
        raw = data.decode("utf-8", errors="replace")

    text = _clean(raw)
    if len(text.split()) < 3:
        raise ResumeParseError(
            "We couldn't find any text in that file. If it's a scanned image, export a text-based PDF or upload a DOCX."
        )
    return text
