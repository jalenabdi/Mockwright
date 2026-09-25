from fastapi import FastAPI
from pydantic import BaseModel
from .behave_questions import get_random_behavioral_question

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