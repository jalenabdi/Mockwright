# Mockwright

> Practice your story. Strengthen your answers. Walk into the interview ready.

## Overview

**Mockwright** is a voice-first behavioral interview practice platform. Users choose a target role and experience level, complete a live five-question interview with an AI interviewer, and receive structured feedback on their answers. A typed-answer option is also available.

The goal is to build a small, reliable MVP with **Python, FastAPI, PostgreSQL, the Deepgram Voice Agent API, and AI-generated feedback**. Real-time one-on-one speaking is a required part of the MVP.

---

## Simple MVP

### Start an Interview

- Enter a target role
- Choose an experience level:
  - Intern
  - Entry-level
  - Junior
  - Senior
- Optionally provide a job description
- Receive five behavioral interview questions

### Complete an Interview

- View one question at a time
- Answer through live voice or text
- Save each answer
- Track interview progress
- Complete the interview after five answers

### Live Voice Interview

- Use the browser microphone to speak with the AI interviewer
- Use the Deepgram Voice Agent API for real-time listening and speaking
- Hear each interview question read aloud
- Receive live transcripts of spoken answers
- Allow the user to interrupt the AI interviewer naturally
- Save voice transcripts through the same answer flow used for typed answers

### Receive Feedback

- Generate a final score out of 100
- Evaluate answers for:
  - Relevance
  - STAR structure
  - Specificity
  - Individual contribution
  - Communication
- Return strengths and areas for improvement
- Recommend one clear next step

### Interview History

- View completed interviews
- Review previous questions and answers
- View saved feedback reports

---

## Not Required for the MVP

These features may be added only after the required MVP is complete:

- Adaptive follow-up questions
- Resume-based questions
- Company-specific interviews
- Progress charts
- Shareable reports
- Multiple interviewer voices
- Multilingual interviews

---

## Tech Stack

- **Language:** Python
- **API Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Data Validation:** Pydantic
- **Authentication:** JWT and password hashing
- **AI Feedback:** LLM API with structured output
- **Live Voice:** [Deepgram Voice Agent API](https://developers.deepgram.com/docs/voice-agent)
- **Real-Time Communication:** WebSockets
- **Testing:** Pytest and FastAPI TestClient
- **API Documentation:** Swagger UI provided by FastAPI

A lightweight browser interface is required for microphone access, live audio, and the voice interview controls. The main engineering focus remains the backend and Deepgram integration.

---

## Eight-Week Backend Plan

Each contributor receives one main task per week. Tasks should remain small enough to complete in one pull request.

### Week 1 — First Working Interview Flow

- **Ahmed Hisham:** Set up the FastAPI application and create a `GET /health` endpoint that confirms the backend is running.
- **Alex:** Create the Pydantic model for starting an interview with `target_role`, `experience_level`, and an optional `job_description`.
- **Krithik:** Create a question bank containing at least 10 behavioral questions and a function that selects five questions.
- **Marcial Amaro:** Create `POST /interviews/start`, which accepts the interview settings and returns five questions from the question bank.

**Week 1 goal:** A user can open Swagger UI, enter their interview settings, and receive five behavioral questions.

### Week 2 — Database Setup

- Configure the PostgreSQL connection with SQLAlchemy.
- Create the interview session model and table.
- Create the question and answer models.
- Save a newly started interview and its five questions.

### Week 3 — Typed Answer Flow

- Create an endpoint that returns the current question.
- Create an endpoint for submitting a typed answer.
- Save submitted answers in PostgreSQL.
- Track progress and complete the interview after five answers.

### Week 4 — User Authentication

- Create the user model and database table.
- Add a user registration endpoint with password hashing.
- Add login and JWT token creation.
- Protect interview routes so users access only their own interviews.

### Week 5 — AI Feedback

- Create the scoring rubric and feedback schema.
- Send completed answers to the AI service.
- Return a score, strengths, improvements, and next step.
- Save the completed feedback report.

### Week 6 — Deepgram Live Voice

- Configure the Deepgram Voice Agent API securely with environment variables.
- Create the WebSocket flow for streaming microphone audio and receiving AI audio.
- Configure the AI interviewer to ask the five interview questions one at a time.
- Capture each final transcript and save it through the existing answer flow.

### Week 7 — History, Testing, and Integration

- Add endpoints for viewing completed interviews and feedback reports.
- Ensure users can access only their own interview history.
- Test the authentication, typed interview, voice interview, and feedback flows.
- Connect the complete application and fix important bugs.

### Week 8 — Containerization, Deployment, and Demo

- Improve error messages and input validation.
- Test the full application from beginning to end.
- Containerize the application and database with Docker.
- Deploy the application, finish the documentation, and prepare the final demo.

---

## MVP Completion Checklist

The MVP is complete when:

- Users can register and log in
- Users can start a five-question behavioral interview
- Users can answer each question through live voice or text
- Deepgram provides real-time transcription and spoken AI responses
- Users can interrupt the AI interviewer while it is speaking
- Voice transcripts are saved as interview answers
- Interview progress is stored in PostgreSQL
- Completed interviews receive structured feedback
- Users can review their previous interviews and reports
- Users cannot access another user's interview data
- The main success and failure cases are tested
- The full flow can be demonstrated through Swagger UI
- The live voice flow can be demonstrated through the browser interface

---

## Suggested Project Structure

```text
mockwright/
├── backend/
│   └── app/
│       ├── main.py
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       ├── routers/
│       │   └── voice.py
│       └── services/
│           └── deepgram.py
├── frontend/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Running the Project

### 1. Clone the Repository

```bash
git clone https://github.com/jalenabdi/Mockwright.git
cd Mockwright
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file from `.env.example` and provide the required values:

```text
DATABASE_URL=your_postgresql_connection_string
SECRET_KEY=your_jwt_secret
DEEPGRAM_API_KEY=your_deepgram_api_key
```

Never commit the `.env` file or any API keys to GitHub.

### 5. Start the Backend

```bash
uvicorn backend.app.main:app --reload
```

### 6. Open the API Documentation

Visit:

```text
http://127.0.0.1:8000/docs
```

---

## Branching Rules

### Main Branch

- Keep `main` stable.
- Do not commit directly to `main`.
- Submit every task through a pull request.
- Only the project manager merges pull requests.

### Feature Branches

Create a branch from the newest version of `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/short_description
```

Examples:

```text
feature/health_endpoint
feature/interview_schema
feature/question_bank
feature/start_interview
feature/deepgram_voice
```

---

## Development Process

1. Receive or select a task.
2. Pull the newest version of `main`.
3. Create a feature branch.
4. Complete only the assigned task.
5. Test the change locally.
6. Push the branch to GitHub.
7. Open a pull request into `main`.
8. Address review feedback and wait for the project manager to merge it.

Keep each branch and pull request focused on one task.

---

## Pull Request Checklist

Before opening a pull request, confirm that:

- The application still runs
- The assigned feature works
- Unrelated files were not changed
- No passwords, API keys, or `.env` files were committed
- The pull request explains what changed and how it was tested

Example pull request title:

```text
Add Deepgram live voice integration
```

---

## Project Status

Mockwright is currently in the first stage of development. The team will build the interview flow in small pieces, then connect the required Deepgram live voice experience before final testing and deployment.
