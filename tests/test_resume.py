"""Resumes: one saved per account, used to tailor interview questions."""
import io
import zipfile

import pytest

from backend.app.services.question_generator import InterviewContext, build_prompt
from backend.app.services.resume_parser import MAX_RESUME_CHARS, ResumeParseError, extract_resume_text


def _pdf(text: str) -> bytes:
    """A minimal one-page PDF whose page says `text`."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def _docx(*paragraphs: str) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return out.getvalue()


RESUME = "Ada Lovelace\nSoftware Engineer Intern, Acme (2025)\nBuilt a Kafka pipeline that cut report time by 60%."
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(client, headers, data: bytes, file_name: str, content_type: str):
    return client.put(
        "/resume",
        params={"file_name": file_name},
        content=data,
        headers={**headers, "Content-Type": content_type},
    )


# --- Parsing ----------------------------------------------------------------

def test_text_is_read_from_pdf_docx_and_txt():
    assert "Kafka pipeline" in extract_resume_text(_pdf("Built a Kafka pipeline"), "cv.pdf")
    assert extract_resume_text(_docx("Ada Lovelace", "Kafka pipeline"), "cv.docx") == "Ada Lovelace\nKafka pipeline"
    assert extract_resume_text(RESUME.encode(), "cv.txt") == RESUME


def test_long_resumes_are_trimmed_and_blank_lines_squeezed():
    text = extract_resume_text(("line\n\n\n\n" * 20_000).encode(), "cv.txt")
    assert len(text) <= MAX_RESUME_CHARS
    assert "\n\n\n" not in text


@pytest.mark.parametrize(
    ("data", "name"),
    [(b"%PDF-1.4 not really a pdf", "cv.pdf"), (b"PK not a docx", "cv.docx"), (b"   \n ", "cv.txt"), (b"\x89PNG", "cv.png")],
)
def test_unreadable_or_unsupported_files_are_rejected(data, name):
    with pytest.raises(ResumeParseError):
        extract_resume_text(data, name)


# --- Endpoints --------------------------------------------------------------

def test_a_resume_is_saved_per_account(client, auth_headers, other_auth_headers):
    assert client.get("/resume", headers=auth_headers).status_code == 404

    saved = _upload(client, auth_headers, _pdf("Built a Kafka pipeline"), "Ada CV.pdf", "application/pdf")
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["file_name"] == "Ada CV.pdf"
    assert "Kafka pipeline" in body["preview"]
    assert body["word_count"] >= 4

    assert client.get("/resume", headers=auth_headers).json()["file_name"] == "Ada CV.pdf"
    assert client.get("/resume", headers=other_auth_headers).status_code == 404


def test_uploading_again_replaces_the_resume(client, auth_headers):
    _upload(client, auth_headers, RESUME.encode(), "old.txt", "text/plain")
    _upload(client, auth_headers, _docx("New resume for Ada"), "new.docx", DOCX_TYPE)
    assert client.get("/resume", headers=auth_headers).json()["file_name"] == "new.docx"


def test_a_resume_can_be_removed(client, auth_headers):
    _upload(client, auth_headers, RESUME.encode(), "cv.txt", "text/plain")
    assert client.delete("/resume", headers=auth_headers).status_code == 204
    assert client.get("/resume", headers=auth_headers).status_code == 404


@pytest.mark.parametrize(
    ("data", "name", "content_type", "status"),
    [
        (b"\x89PNG fake", "photo.png", "image/png", 415),
        (b"%PDF-1.4 broken", "scan.pdf", "application/pdf", 422),
        (b"x" * (5 * 1024 * 1024 + 1), "huge.txt", "text/plain", 413),
    ],
)
def test_bad_uploads_get_clear_errors(client, auth_headers, data, name, content_type, status):
    assert _upload(client, auth_headers, data, name, content_type).status_code == status
    assert client.get("/resume", headers=auth_headers).status_code == 404


def test_resume_endpoints_require_sign_in(client):
    assert client.get("/resume").status_code == 401


# --- Interviews -------------------------------------------------------------

def test_an_interview_can_be_based_on_my_resume(client, auth_headers, start_interview, answer_current, question_generator):
    _upload(client, auth_headers, RESUME.encode(), "cv.txt", "text/plain")

    interview = start_interview(use_resume=True)

    assert interview["used_resume"] is True
    first_context = question_generator.calls[0][0]
    assert "Kafka pipeline" in first_context.resume
    # Later questions see it too, even after the saved resume changes.
    _upload(client, auth_headers, b"A different resume", "new.txt", "text/plain")
    answer_current(interview)
    assert "Kafka pipeline" in question_generator.step_calls[-1]["context"].resume


def test_interviews_ignore_the_resume_unless_asked(client, auth_headers, start_interview, question_generator):
    _upload(client, auth_headers, RESUME.encode(), "cv.txt", "text/plain")
    interview = start_interview()
    assert interview["used_resume"] is False
    assert question_generator.calls[0][0].resume is None


def test_using_a_resume_needs_one_saved(client, auth_headers, question_generator):
    response = client.post(
        "/interviews/start",
        json={"target_role": "Engineer", "experience_level": "intern", "use_resume": True},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_the_question_prompt_includes_the_resume():
    context = InterviewContext("Software Engineer", "intern", None, resume=RESUME)
    assert "Kafka pipeline" in build_prompt(context, [])
    assert "candidate_resume" not in build_prompt(InterviewContext("Software Engineer", "intern", None), [])
