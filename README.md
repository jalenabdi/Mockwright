# Mockwright

> Practice your story. Strengthen your answers. Walk into the interview ready.

## Overview

**Mockwright** is a backend-focused behavioral interview practice platform. Users choose a target role and experience level, complete a five-question interview, and receive structured feedback on their answers.

The goal is to build a small, reliable MVP with **Python, FastAPI, PostgreSQL, and AI-generated feedback**. The team will finish the typed interview experience before considering more advanced features.

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
- Submit a typed answer
- Save each answer
- Track interview progress
- Complete the interview after five answers

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

These features may be added only after the typed interview flow is complete:

- Voice answers and transcription
- Real-time AI conversations
- Barge-in and interruption support
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
- **Testing:** Pytest and FastAPI TestClient
- **API Documentation:** Swagger UI provided by FastAPI

A lightweight frontend may be created later to demonstrate the API, but the team will focus on the backend MVP first.

---

## Eight-Week Backend Plan

Each contributor receives one main task per week. Tasks should remain small enough to complete in one pull request.

### Week 1 — First Working Interview Flow

- Set up the FastAPI application and create a `GET /health` endpoint that confirms the backend is running.
- Create the Pydantic model for starting an interview with `target_role`, `experience_level`, and an optional `job_description`.
- Create a question bank containing at least 10 behavioral questions and a function that selects five questions.
- Create `POST /interviews/start`, which accepts the interview settings and returns five questions from the question bank.

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

### Week 6 — Interview History

- Create an endpoint for listing completed interviews.
- Create an endpoint for viewing one completed interview.
- Return the saved questions, answers, and feedback.
- Test that users cannot access another user's interviews.

### Week 7 — Testing and Integration

- Test registration, login, and protected routes.
- Test starting and completing an interview.
- Test AI feedback and invalid responses.
- Connect the complete flow and fix important bugs.

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
- Users can submit one typed answer per question
- Interview progress is stored in PostgreSQL
- Completed interviews receive structured feedback
- Users can review their previous interviews and reports
- Users cannot access another user's interview data
- The main success and failure cases are tested
- The full flow can be demonstrated through Swagger UI

---

## Suggested Project Structure

```text
mockwright/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   └── services/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Running the Project

### 1. Clone the repository

```bash
git clone https://github.com/jalenabdi/Mockwright.git
cd Mockwright
```

### 2. Create a virtual environment

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Backend

```bash
uvicorn app.main:app --reload
```

### 5. Open the API Documentation

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
Add interview question bank
```

---
