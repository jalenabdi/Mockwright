# Mockwright

> Practice your story. Strengthen your answers. Walk into the interview ready.

## Overview

**Mockwright** is a backend-focused, AI-powered behavioral interview practice platform. Users choose a target role and experience level, answer five behavioral questions, and receive structured feedback on their performance.

The primary goal of this project is to build a reliable backend with **FastAPI**, **PostgreSQL**, authentication, interview session management, AI-generated feedback, voice transcription, automated testing, and deployment. A lightweight interface may be used to demonstrate the API, but the eight-week development plan focuses on backend engineering.

---

## Core Backend MVP

### Authentication

- Register users with an email and password
- Hash passwords before storing them
- Log users in with JWT authentication
- Protect private API routes
- Return clear authentication and validation errors

### Interview Setup

- Accept a target role
- Accept an experience level:
  - Intern
  - Entry-level
  - Junior
  - Senior
- Accept an optional job description
- Create a new interview session
- Generate and store five behavioral questions

### Interview Sessions

- Return one question at a time
- Accept and save a typed answer
- Track the current question and interview progress
- Prevent users from skipping required questions
- Mark the interview as completed after five answers
- Ensure users can access only their own interviews

### AI Scoring and Feedback

- Evaluate completed interviews with an LLM API
- Require structured output validated by Pydantic
- Generate a final score out of 100
- Evaluate answers using:
  - Relevance
  - STAR structure
  - Specificity
  - Individual contribution
  - Communication
- Return strengths and areas for improvement
- Recommend one clear next step
- Save the completed feedback report

### Basic Voice Support

- Accept an uploaded audio recording
- Validate the file before processing it
- Send the audio to the Deepgram API
- Return the generated transcript
- Allow the transcript to be submitted through the same answer endpoint used for typed responses

### Interview History

- Return a user's completed interviews
- Return the questions and answers from a selected interview
- Return the saved feedback report
- Prevent users from viewing another user's history

---

## Stretch Goals

- Real-time voice conversations
- Barge-in so users can interrupt the AI interviewer
- Adaptive follow-up questions
- Different interview lengths
- Resume-based questions
- Behavioral story bank
- Progress analytics
- Company-specific question sets
- Shareable or downloadable reports
- Multiple interviewer voices
- Multilingual interview practice

---

## Tech Stack

### Backend

- **API Framework:** Python + FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Validation:** Pydantic
- **Authentication:** JWT + password hashing
- **AI Evaluation:** An LLM API with structured Pydantic output
- **Speech-to-Text:** Deepgram API
- **Advanced Voice — Stretch Goal:** Deepgram Voice Agent API
- **Testing:** Pytest + HTTPX / FastAPI TestClient
- **Containerization:** Docker + Docker Compose
- **Continuous Integration:** GitHub Actions
- **Deployment:** A Docker-compatible cloud platform

### Supporting Interface

- **Frontend:** Next.js + TypeScript + Tailwind CSS
- **Data Fetching:** TanStack Query

The interface exists to demonstrate and consume the backend API. The main project work and weekly milestones are centered on backend development.

---

## Eight-Week Backend Plan

*Each bullet represents one contributor's main task for the week. This plan covers application development and testing; final release setup will be handled separately by the project manager.*

### Week 1 — Project Setup

- Set up the FastAPI project and GitHub repository
- Connect the application to PostgreSQL
- Create a health-check endpoint to confirm the backend works
- Add a simple automated test for the health-check endpoint

### Week 2 — User Authentication

- Create the user model and database table
- Add the user registration endpoint
- Add login and JWT token creation
- Protect a route and test the authentication flow

### Week 3 — Interview Setup

- Create the interview session model
- Create the interview question model
- Add an endpoint for starting an interview
- Generate and save five behavioral questions

### Week 4 — Typed Interview

- Return one interview question at a time
- Add an endpoint for submitting typed answers
- Save each answer in PostgreSQL
- Track progress and complete the interview after five answers

### Week 5 — Feedback

- Create the scoring rubric and feedback schema
- Send completed answers to the AI evaluation service
- Generate the score, strengths, and areas for improvement
- Save and return the final feedback report

### Week 6 — Basic Voice Mode

- Add an endpoint for uploading an audio answer
- Validate the uploaded audio file
- Use Deepgram to convert the audio into text
- Submit the transcript through the existing answer flow

### Week 7 — History and Testing

- Add endpoints for viewing past interviews and reports
- Make sure users can access only their own interviews
- Test the main authentication and interview routes
- Connect the full flow and fix important bugs

### Week 8 — Final Testing and Demo

- Test registration, login, and protected routes
- Test the complete typed interview flow
- Test AI feedback, interview history, and voice transcription
- Fix final bugs and finish the documentation and demo

---

## MVP Completion Checklist

The backend MVP is complete when:

- Users can register and log in securely
- Protected routes require a valid JWT
- Users can create and complete a five-question interview
- Questions, answers, progress, and reports are stored in PostgreSQL
- Completed interviews receive structured AI feedback
- Audio responses can be transcribed and submitted as text
- Users can review their previous interviews and reports
- Users cannot access another user's data
- Important success and failure cases are covered by automated tests
- The API is deployed and documented

---

## Branching Rules

### Main Branch

- `main` must always remain stable.
- Do not commit directly to `main`.
- All changes must enter through an approved pull request.

### Feature Branches

Create every branch from the latest version of `main`.

Use this naming pattern:

```text
type/short_description
```

Examples:

```text
feature/auth_jwt
feature/interview_sessions
feature/answer_submission
feature/ai_feedback
feature/voice_transcription
fix/login_error
test/interview_routes
```

Create a branch with:

```bash
git checkout main
git pull origin main
git checkout -b feature/interview_sessions
```

---

## Development Process

1. Select or receive a GitHub issue.
2. Pull the newest version of `main`.
3. Create a branch for the issue.
4. Implement and test the change.
5. Push the branch to GitHub.
6. Open a pull request into `main`.
7. Address review feedback.
8. Wait for the project manager to merge the pull request.

Keep each branch and pull request focused on one task.

---

## Pull Request Rules

- Every code change requires a pull request.
- A pull request must include:
  - A clear description of the change
  - A summary of the files or features added
  - Testing that was performed
  - Database changes, if applicable
  - API request and response examples, if applicable
  - Any known issues
- At least one teammate must review the pull request.
- The author cannot approve or merge their own pull request.
- Only the project manager performs the final merge into `main`.
- Never commit passwords, API keys, `.env` files, or other secrets.

Example pull request title:

```text
Add interview session endpoint
```

---

## Example Workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/interview_sessions

# Implement and test the feature

git add .
git commit -m "Add interview session endpoint"
git push origin feature/interview_sessions
```

Then open a pull request, request a review, address any feedback, and wait for the project manager to merge it.

---

## Resources

### Everyone Should Watch

- [Git and GitHub for Beginners — Crash Course](https://www.youtube.com/watch?v=RGOj5yH7evk)
- [What Is a REST API?](https://www.youtube.com/watch?v=lsMQRaeKNDk)
- [Docker Compose Tutorial](https://www.youtube.com/watch?v=MVIcrmeV_6c)
- [System Design for Beginners](https://www.youtube.com/watch?v=m8Icp_Cid5o)

### Backend Team

- [FastAPI Course for Beginners](https://www.youtube.com/watch?v=tLKKmouUams)
- [Python API Development — Comprehensive Course](https://www.youtube.com/watch?v=0sOvCWFmrtA)
- [PostgreSQL Full Course for Beginners](https://www.youtube.com/watch?v=qw--VYLpxG4)
- [Pytest Tutorial — How to Test Python Code](https://www.youtube.com/watch?v=cHYq1MRoyI0)

> Some videos may use older library versions. Use them to learn the concepts, then check the current official documentation while implementing features.

---

## Project Status

Mockwright is currently in the planning and setup stage. The team will build and stabilize the typed interview backend before adding voice transcription and advanced voice features.
