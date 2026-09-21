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
- **AI Feedback:** Gemini API with structured output
- **Live Voice:** [Deepgram Voice Agent API](https://developers.deepgram.com/docs/voice-agent)
- **Real-Time Communication:** WebSockets
- **Testing:** Pytest and FastAPI TestClient
- **API Documentation:** Swagger UI provided by FastAPI

A lightweight browser interface is required for microphone access, live audio, and the voice interview controls. The main engineering focus remains the backend and Deepgram integration.

---

## Eight-Week MVP Plan

Each contributor receives one main task per week. Tasks are listed in the recommended merge order and should remain small enough to complete in one pull request.

### Week 1 — First Working Interview Flow

- **Alex:** Set up the FastAPI application and create a `GET /health` endpoint that confirms the backend is running.
- **Krithik:** Create the `StartInterviewRequest` Pydantic model with `target_role`, `experience_level`, and an optional `job_description`. Restrict `experience_level` to the four supported choices.
- **Ahmed:** Create a question bank containing at least 10 behavioral questions and a `select_questions(count=5)` function that returns five unique questions.
- **Marcial:** Create `POST /interviews/start`, which validates the request with `StartInterviewRequest` and returns the submitted settings with five selected questions.

**Week 1 goal:** A user can open Swagger UI, submit valid interview settings, and receive exactly five unique behavioral questions. No database is required yet.

### Week 2 — Database Setup

- **Ahmed:** Create `database.py` with the SQLAlchemy engine, session factory, `get_db` dependency, and `DATABASE_URL` environment-variable configuration.
- **Alex:** Create the `Interview` SQLAlchemy model with its settings, status, current-question position, and timestamps. Create the first Alembic migration.
- **Krithik:** Create the `InterviewQuestion` and `Answer` SQLAlchemy models, relationships, question order field, and a rule allowing only one answer per interview question. Add the required migration.
- **Marcial:** Update `POST /interviews/start` so one database transaction saves the interview and its five selected questions, then returns the new `interview_id` and questions.

**Week 2 goal:** Starting an interview creates one interview row and five ordered question rows in PostgreSQL, and the schema can be created from Alembic migrations.

### Week 3 — Typed Answer Flow

- **Ahmed:** Create `GET /interviews/{interview_id}/current-question`, which returns the next unanswered question and a clear error for an unknown or completed interview.
- **Alex:** Create the typed-answer Pydantic schemas and `POST /interviews/{interview_id}/answers`. Reject blank answers, questions that do not belong to the interview, and duplicate submissions.
- **Krithik:** Create an interview service that saves an answer, advances the current-question position, and changes the interview status to `completed` after the fifth answer.
- **Marcial:** Create `GET /interviews/{interview_id}` to return the interview status, answered count, total question count, and current question number. Verify the complete typed flow in Swagger UI.

**Week 3 goal:** A user can answer the five questions in order, refresh without losing progress, and see the interview become completed after the fifth answer.

### Week 4 — User Authentication

- **Ahmed:** Create the `User` model with a unique email and hashed-password field, then add the Alembic migration.
- **Alex:** Create `POST /auth/register`. Validate the input, reject duplicate emails, and hash passwords with `pwdlib` and Argon2 before saving them.
- **Krithik:** Create `POST /auth/token` using `OAuth2PasswordRequestForm`. Verify the password and return a signed JWT with a subject and expiration time.
- **Marcial:** Create the `get_current_user` dependency, associate every interview with its owner, and protect all interview routes so users can access only their own records.

**Week 4 goal:** A user can register, log in, and use a bearer token, while requests for another user's interview are rejected.

### Week 5 — AI Feedback

- **Ahmed:** Create the feedback rubric and Pydantic response schema. Score relevance, STAR structure, specificity, individual contribution, and communication from 0–20 so the total is 0–100.
- **Alex:** Create a Gemini feedback service that receives the five question-and-answer pairs and requests structured output matching the feedback schema. Read `GEMINI_API_KEY` from the environment.
- **Krithik:** Create the `Feedback` model and migration with a one-to-one relationship to `Interview` so each interview can have only one saved report.
- **Marcial:** Create `POST /interviews/{interview_id}/feedback`. Allow it only for the interview owner after all five answers are saved, persist the result, return the saved report on repeated requests, and return a controlled error if Gemini fails or returns invalid data.

**Week 5 goal:** A completed interview receives one saved, structured report containing the total score, category scores, strengths, improvements, and one next step.

### Week 6 — Deepgram Live Voice

- **Ahmed:** Create the Deepgram service that reads `DEEPGRAM_API_KEY` from the environment, opens the Voice Agent connection, waits for `Welcome`, sends `Settings`, and waits for `SettingsApplied`. Configure the interviewer prompt to ask the five stored questions one at a time.
- **Alex:** Create the WebSocket endpoint at `/interviews/{interview_id}/voice`. Validate the JWT sent in the first client message, verify interview ownership, connect through the Deepgram service, and relay binary PCM audio and Deepgram events in both directions.
- **Krithik:** Build the lightweight browser voice screen with microphone permission, start/stop controls, connection status, transcript display, PCM microphone capture, AI audio playback, and immediate playback cancellation when `UserStartedSpeaking` is received.
- **Marcial:** Convert each final user transcript into an answer by calling the existing answer service, advance interview progress, and end the voice session after the fifth saved answer.

**Week 6 goal:** A user can complete all five questions in a live browser conversation, hear the interviewer, interrupt naturally, see transcripts, and find the five voice answers saved in PostgreSQL.

### Week 7 — History, Testing, and Integration

- **Ahmed:** Create `GET /interviews` for the signed-in user's interview list and expand `GET /interviews/{interview_id}` to return saved questions, answers, status, and progress.
- **Alex:** Create `GET /interviews/{interview_id}/feedback` and apply the same ownership check to the interview list, interview detail, and feedback queries.
- **Krithik:** Add Pytest tests for registration, login, interview ownership, interview creation, typed answers, completion, feedback retrieval, and history using an isolated test database.
- **Marcial:** Add WebSocket tests with a fake Deepgram connection and mock Gemini responses so tests use no API credits. Run one manual end-to-end voice test and fix blocking integration bugs.

**Week 7 goal:** Interview history works securely, the main HTTP and WebSocket flows are tested, and automated tests do not call paid external APIs.

### Week 8 — Containerization, Deployment, and Demo

- **Ahmed:** Review input validation and error responses across the API, remove unclear server errors, and update `.env.example` without including real secrets.
- **Alex:** Create the backend `Dockerfile` and a Docker Compose configuration for FastAPI and PostgreSQL, including service health checks and a repeatable migration command.
- **Krithik:** Deploy the FastAPI service and PostgreSQL database, configure production environment variables, run the migrations, and confirm that HTTPS and `wss://` connections work.
- **Marcial:** Run the final smoke-test checklist for registration, typed and voice interviews, feedback, and history. Finish the README and prepare a short demo script using a fresh user account.

**Week 8 goal:** The containerized application can be deployed from a clean environment and demonstrated from registration through a completed voice interview, saved feedback, and history.

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
- The complete HTTP flow can be demonstrated through Swagger UI
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
GEMINI_API_KEY=your_gemini_api_key
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

## Resources

This curriculum is for **Ahmed Hisham, Alex, Krithik, and Marcial Amaro**. It is intentionally video-heavy, but every week also includes official documentation that should be treated as the source of truth.

### How to Use This Guide

1. Before starting a task, watch the listed **Watch First** video or relevant chapter.
2. Keep the listed **Official References** open while writing code.
3. Build only the small Mockwright feature assigned for that week; do not copy an entire tutorial project.
4. Complete the **Checkpoint** before opening a pull request.
5. If a video and the current documentation disagree, follow the documentation. Frameworks, SDKs, and authentication libraries change over time.

The long FastAPI course below is a reference library. Nobody needs to watch all of it before Week 1.

### Shared Foundation — Complete Before or During Week 1

#### Watch First

- [Learn Python — Full Course for Beginners](https://www.youtube.com/watch?v=rfscVS0vtbw) — Use this only if Python functions, lists, dictionaries, modules, classes, or virtual environments are unfamiliar.
- [Git and GitHub for Beginners — Crash Course](https://www.youtube.com/watch?v=RGOj5yH7evk) — Learn cloning, commits, branches, pushing, pulling, and pull requests.
- [What Is a REST API?](https://www.youtube.com/watch?v=SLwpqD8n3d0) — A short explanation of HTTP requests, endpoints, and JSON responses.
- [FastAPI Course for Beginners](https://www.youtube.com/watch?v=tLKKmouUams) — An overview of routes, request bodies, validation, and Swagger UI.
- [Python API Development — Comprehensive Course for Beginners](https://www.youtube.com/watch?v=0sOvCWFmrtA) — Use the chapter list to revisit FastAPI, PostgreSQL, JWT authentication, testing, and deployment throughout the project.

#### Team Checkpoint

Every contributor should be able to clone the repository, create a branch, activate a virtual environment, install dependencies, run Uvicorn, open `/docs`, commit a change, and push the branch.

### Week 1 — FastAPI, Pydantic, and the First Interview Flow

#### Watch First

- [FastAPI Course for Beginners](https://www.youtube.com/watch?v=tLKKmouUams) — Focus on path operations, request bodies, Pydantic models, and automatic API documentation.
- [Python Random Module Tutorial](https://www.youtube.com/watch?v=KzqSDvzOFNA) — Focus on selecting items from a list. Mockwright should use `random.sample()` so the five questions are unique.
- [How to Use FastAPI APIRouter](https://www.youtube.com/watch?v=uHPk5R4xGkM) — Use this when moving interview endpoints out of `main.py`.

#### Official References

- [FastAPI: First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/) — Create the application and `GET /health`.
- [FastAPI: Request Body](https://fastapi.tiangolo.com/tutorial/body/) — Accept the interview settings as JSON.
- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/) — Define and validate `target_role`, `experience_level`, and `job_description`.
- [Python random.sample](https://docs.python.org/3/library/random.html#random.sample) — Return five different questions without modifying the original bank.
- [FastAPI: Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) — Organize endpoints with `APIRouter`.

#### Checkpoint

`GET /health` returns a success response, invalid interview input receives a validation error, and `POST /interviews/start` returns exactly five unique questions in Swagger UI.

### Week 2 — PostgreSQL, SQLAlchemy, and Migrations

#### Watch First

- [Learn PostgreSQL Tutorial — Full Course for Beginners](https://www.youtube.com/watch?v=qw--VYLpxG4) — Focus on tables, primary keys, foreign keys, inserts, selects, updates, and joins.
- [Python FastAPI Tutorial: PostgreSQL and Alembic](https://www.youtube.com/watch?v=e8NnDz8uT7o) — See how a FastAPI application connects models to PostgreSQL and manages schema changes.
- [Python API Development — Comprehensive Course for Beginners](https://www.youtube.com/watch?v=0sOvCWFmrtA) — Use the PostgreSQL, SQLAlchemy, and database migration chapters as a second explanation.

#### Official References

- [PostgreSQL Downloads](https://www.postgresql.org/download/) — Install PostgreSQL locally if the team is not using Docker yet.
- [FastAPI: SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/) — Learn how database sessions fit into FastAPI.
- [SQLAlchemy 2.0 Unified Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) — Use modern SQLAlchemy 2.x syntax for engines, sessions, inserts, and queries.
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) — Create migration files instead of recreating tables manually.

#### Checkpoint

Starting an interview creates one interview row and five related question rows in PostgreSQL. A fresh database can be brought up to date by running the migrations.

### Week 3 — Typed Answers and Interview Progress

#### Watch First

- [Python API Development — Comprehensive Course for Beginners](https://www.youtube.com/watch?v=0sOvCWFmrtA) — Rewatch the CRUD, SQLAlchemy query, response model, and error-handling chapters.
- [FastAPI and PostgreSQL Route Building](https://www.youtube.com/watch?v=gAvdCeE7Gh4) — Use this as a focused example of connecting API routes to PostgreSQL operations.

#### Official References

- [FastAPI: Response Models](https://fastapi.tiangolo.com/tutorial/response-model/) — Return predictable question, answer, and progress responses.
- [FastAPI: Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) — Return clear `404`, `409`, and validation errors.
- [FastAPI: Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) — Inject a database session without duplicating setup code in every route.
- [SQLAlchemy ORM Querying Guide](https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html) — Load the current question and save answers with SQLAlchemy 2.x.

#### Checkpoint

A user can fetch the current question, submit one typed answer, refresh the page without losing progress, and complete the interview only after five answers.

### Week 4 — Password Hashing and JWT Authentication

#### Watch First

- [JWT Authentication Explained](https://www.youtube.com/watch?v=7Q17ubqLfaM) — Understand the header, payload, signature, expiration, and why a JWT is signed rather than encrypted.
- [Python API Development — Comprehensive Course for Beginners](https://www.youtube.com/watch?v=0sOvCWFmrtA) — Watch the password hashing, login, OAuth2, JWT, protected route, and ownership chapters.

#### Official References

- [FastAPI: OAuth2 with Password Hashing and JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) — Follow the current implementation using `PyJWT` and `pwdlib` with Argon2.
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — Understand why passwords must be hashed and never stored or logged as plain text.
- [Introduction to JSON Web Tokens](https://jwt.io/introduction) — Review token structure and claims such as `sub` and `exp`.

#### Important Version Note

Some older FastAPI videos use `python-jose` and `passlib`. Use the current FastAPI documentation for dependency names and code patterns.

Never place passwords, the JWT secret, or tokens in logs or GitHub.

#### Checkpoint

A user can register, log in, receive a token, access a protected interview route, and receive `401 Unauthorized` without a valid token. A user must receive `404` or `403` when attempting to access another user's interview.

### Week 5 — AI-Generated Structured Feedback

Use one provider for final scoring. The recommended beginner path is the **Gemini API with structured output**.

Deepgram remains responsible for the live voice conversation in Week 6. Gemini evaluates the saved interview transcript after the five answers are complete.

#### Watch First

- [Prompt Engineering Tutorial](https://www.youtube.com/watch?v=_ZvnD73m40o) — Focus on clear instructions, rubrics, constraints, and examples rather than advanced agent features.
- [Python API Development — Comprehensive Course for Beginners](https://www.youtube.com/watch?v=0sOvCWFmrtA) — Revisit environment variables, service-layer organization, error handling, and tests for external services.

#### Official References

- [Gemini API: Getting Started with Python](https://ai.google.dev/gemini-api/docs/get-started) — Install the SDK, create a client, and make the first request.
- [Gemini API: Structured Output](https://ai.google.dev/gemini-api/docs/structured-output) — Require the model to return data matching the feedback schema.
- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/) — Define the score, category scores, strengths, improvements, and next step.
- [Twelve-Factor App: Config](https://12factor.net/config) — Keep the API key in an environment variable.

#### Checkpoint

Given five saved answers, the feedback service returns structured data containing:

- A total score from 0 to 100
- Relevance score
- STAR structure score
- Specificity score
- Individual contribution score
- Communication score
- Strengths
- Areas for improvement
- One recommended next step

A malformed or failed AI response should produce a controlled error instead of crashing the application.

### Week 6 — Deepgram Live Voice and Browser Audio

This is the most integration-heavy week. Begin with a small microphone-to-Deepgram proof of concept before connecting interviews or the database.

#### Watch First

- [Deepgram Voice Agent API Quickstart](https://www.youtube.com/watch?v=A0ovpzPMkOo) — Start here for the shortest product-specific walkthrough.
- [Deepgram Voice Agent API](https://www.youtube.com/watch?v=w_bhgRU1abE) — See the complete listening, thinking, speaking, and interruption flow.
- [WebSockets: How They Work and Why They Are Useful](https://www.youtube.com/watch?v=KPfi5sRiRVY) — Understand persistent two-way communication before implementing audio streaming.
- [Build a WebSocket App with FastAPI and JavaScript](https://www.youtube.com/watch?v=5o__C9wJHZA) — Practice moving messages between a browser and FastAPI.
- [Recording a Browser Media Stream](https://www.youtube.com/watch?v=6b6pLt-lYg8) — Use this for microphone-stream concepts only. The actual Deepgram stream must send the PCM format declared in the Voice Agent settings.

#### Official Deepgram References

- [Voice Agent: Getting Started](https://developers.deepgram.com/docs/voice-agent) — Understand the single WebSocket listening, thinking, and speaking pipeline.
- [Voice Agent Architecture](https://developers.deepgram.com/docs/voice-agent-architecture) — Learn the message flow, transcripts, audio responses, turn detection, and interruptions.
- [Voice Agent Message Flow](https://developers.deepgram.com/docs/voice-agent-message-flow) — Follow the required `Welcome`, `Settings`, `SettingsApplied`, PCM audio, server-event, and barge-in sequence.
- [Build a Voice Agent with Python](https://developers.deepgram.com/docs/build-a-voice-agent-python) — Create a small Python proof of concept before integrating FastAPI.
- [Voice Agent Template Apps](https://developers.deepgram.com/docs/voice-agent-template-apps) — Study a working sample instead of inventing the audio protocol from scratch.
- [Audio Preprocessing and Barge-In](https://developers.deepgram.com/voice-agent/optimize/audio-preprocessing-barge-in) — Implement natural interruption behavior.
- [Deepgram Python SDK](https://github.com/deepgram/deepgram-python-sdk) — Check the current SDK installation instructions and examples.

#### Browser and FastAPI References

- [MDN: getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia) — Request microphone permission safely.
- [MDN: Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) — Read and process live microphone samples for PCM streaming and play received audio.
- [MDN: AudioWorklet](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet) — Process microphone audio without blocking the browser's main interface.
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket) — Send and receive browser data over a persistent connection.
- [FastAPI: WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) — Accept the browser WebSocket and handle disconnects.

#### Security Rule

Never put `DEEPGRAM_API_KEY` in browser JavaScript or commit it to GitHub.

The browser should connect to the FastAPI WebSocket and send its JWT in the first client message. After validating that token and the interview owner, the backend should use the secret when connecting to Deepgram.

#### Checkpoint

The backend waits for `Welcome`, sends `Settings`, waits for `SettingsApplied`, and then relays PCM audio.

The browser can:

- Request microphone access
- Stream live microphone audio
- Play the AI interviewer's audio
- Display final transcripts
- Stop playback when `UserStartedSpeaking` is received
- Save each final transcript through the typed-answer service

### Week 7 — History, Authorization, and Testing

#### Watch First

- [Pytest Tutorial — How to Test Python Code](https://www.youtube.com/watch?v=cHYq1MRoyI0) — Learn test discovery, assertions, fixtures, parametrization, and mocking.
- [Python API Development — Comprehensive Course for Beginners](https://www.youtube.com/watch?v=0sOvCWFmrtA) — Watch the testing database, fixtures, authentication tests, and continuous integration chapters.

#### Official References

- [FastAPI: Testing](https://fastapi.tiangolo.com/tutorial/testing/) — Test HTTP endpoints with `TestClient`.
- [FastAPI: Testing WebSockets](https://fastapi.tiangolo.com/advanced/testing-websockets/) — Test connections, messages, and disconnect behavior.
- [Pytest: Get Started](https://docs.pytest.org/en/stable/getting-started.html) — Use the current Pytest conventions.
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html) — Replace Gemini and Deepgram network calls with predictable fake responses during tests.

#### Checkpoint

Tests cover:

- Registration
- Login
- Interview ownership
- Starting an interview
- Typed answers
- Interview completion
- Structured feedback
- Interview history
- The main WebSocket message flow

Tests must not spend real Gemini or Deepgram API credits.

### Week 8 — Containerization, Deployment, and Demo

Use **Render** as the recommended beginner deployment path: one FastAPI web service and one managed PostgreSQL database.

Pricing and free-plan limits can change, so check the current plans before creating resources.

#### Watch First

- [Docker Tutorial for Beginners](https://www.youtube.com/watch?v=pTFZFxd4hOI) — Learn about images, containers, ports, environment variables, and Dockerfiles.
- [Docker Compose Tutorial](https://www.youtube.com/watch?v=MVIcrmeV_6c) — Run the FastAPI application and PostgreSQL together for local development.
- [GitHub Actions for Beginners](https://www.youtube.com/watch?v=BQrohJ3PT7I) — Optional: run the test suite automatically on pull requests.

#### Official References

- [FastAPI in Containers — Docker](https://fastapi.tiangolo.com/deployment/docker/) — Build a production-ready FastAPI image.
- [Docker Compose Quickstart](https://docs.docker.com/compose/gettingstarted/) — Define the backend and local PostgreSQL services.
- [Render: Deploy a FastAPI App](https://render.com/docs/deploy-fastapi) — Connect the GitHub repository and configure the build and start commands.
- [Render: Create and Connect to PostgreSQL](https://render.com/docs/postgresql-creating-connecting) — Set `DATABASE_URL` and keep the service and database in the same region.
- [Render: WebSockets](https://render.com/docs/websocket) — Use `wss://` in production and plan for reconnects and service restarts.
- [GitHub Actions: Build and Test Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) — Optional continuous integration for Pytest.

#### Checkpoint

Before the final demonstration, confirm that:

- `docker compose up` starts the backend and database locally
- Database migrations run successfully
- All tests pass
- The deployed health endpoint works over HTTPS
- The production voice connection uses `wss://`
- Secrets exist only in deployment environment variables
- The team can demonstrate one complete voice interview from start through saved feedback and history

### Recommended Learning Order

Each contributor should follow the same process, even when another person owns the week's main pull request:

1. Watch the first video for the current week.
2. Read the official page directly related to the assigned task.
3. Build the smallest isolated proof of concept.
4. Add it to Mockwright behind a focused route, schema, model, or service.
5. Test the success case, one invalid-input case, and one dependency-failure case.
