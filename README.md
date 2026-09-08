# Mockwright

> Practice your story. Strengthen your answers. Walk into the interview ready.

## Overview

- **Mockwright** is an AI-powered behavioral interview practice platform for candidates preparing for internships, entry-level positions, junior roles, and senior opportunities.
- Users choose a target role, select their experience level, and optionally provide a job description so the interview can be tailored to the opportunity.
- The AI interviewer asks questions aloud and supports both spoken and typed responses.
- Voice mode is designed to feel conversational, including follow-up questions and the ability to interrupt the interviewer naturally using **barge-in**.
- After the interview, Mockwright provides a score out of 100 and actionable feedback on answer structure, relevance, specificity, individual contribution, communication, and areas for improvement.
- The first release will focus on five-to-seven-question interviews that can be completed within a realistic eight-week development sprint.

---

## MVP

- **Authentication:**
  - Email and password registration
  - Secure password hashing
  - JWT-based login and protected routes
  - Basic candidate profile

- **Interview Setup:**
  - Enter a target position
  - Optionally paste a job description
  - Select an experience level:
    - Intern
    - Entry-level
    - Junior
    - Senior
  - Choose between voice and typed-answer modes
  - Generate five to seven behavioral questions

- **AI Interview Experience:**
  - AI-generated questions based on the selected role and experience level
  - Questions spoken aloud by the AI interviewer
  - Real-time voice conversation through the Deepgram Voice Agent API
  - Speech-to-text transcription for spoken answers
  - Barge-in support so users can interrupt the interviewer while it is speaking
  - Typed responses for users without a microphone
  - Clear listening, thinking, speaking, and disconnected states

- **Adaptive Follow-Ups:**
  - Ask for missing context when an answer is incomplete
  - Request the user's individual contribution when an answer relies too heavily on â€œweâ€
  - Ask for measurable results when impact is unclear
  - Avoid unnecessary or repeated follow-up questions

- **Scoring and Feedback:**
  - Final practice score out of 100
  - Feedback based on:
    - Relevance
    - STAR structure
    - Specificity and evidence
    - Individual ownership and judgment
    - Reflection and communication
  - Written strengths and areas for improvement
  - Suggested next step for future practice
  - Voice-delivery observations displayed separately from answer-content scoring

- **Interview History:**
  - View completed interviews
  - Review previous questions and transcripts
  - Revisit scores and feedback reports
  - Delete personal interview history

---

## Stretch Goals

- **Behavioral Story Bank:**
  - Save reusable stories from work, school, projects, and leadership experiences
  - Match stories to competencies such as teamwork, ownership, conflict, failure, and leadership

- **Competency Coverage Map:**
  - Show which behavioral topics a user has practiced
  - Identify areas where the user needs a stronger example

- **Progress Tracking:**
  - Compare scores across multiple interviews
  - Visualize improvement by feedback category
  - Recommend the next skill to practice

- **Resume-Aware Practice:**
  - Allow users to provide resume information
  - Generate questions connected to their actual experience

- **Expanded Interview Modes:**
  - Short, standard, and extended interview lengths
  - Company-style question sets
  - Additional industries and career fields
  - Multilingual interview practice

- **Report Sharing:**
  - Export a private feedback summary
  - Share selected results with a mentor or career coach

- **Accessibility Improvements:**
  - Keyboard-first interview controls
  - Caption customization
  - Adjustable speech speed and interviewer voice

---

## Tech Stack

- **Frontend:** Next.js + TypeScript + Tailwind CSS
- **API:** Python + FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Validation:** Pydantic
- **Authentication:** JWT with PyJWT and password hashing
- **Voice AI:** Deepgram Voice Agent API
- **Real-Time Audio:** Browser media APIs + WebSockets
- **Frontend Data Fetching:** TanStack Query
- **API Documentation:** OpenAPI and Swagger UI through FastAPI
- **Testing:**
  - Pytest for backend unit and integration tests
  - HTTPX / FastAPI TestClient for API testing
  - Playwright for critical end-to-end flows
  - Postman for manual API testing
- **Containerization:** Docker + Docker Compose
- **Continuous Integration:** GitHub Actions
- **Deployment:** Render Blueprint or another Docker-compatible cloud host

---

## Timeline

*The timeline may change as the team tests the voice experience and receives user feedback.*

- **Week 1 â€” Foundation:**
  - Confirm the MVP and assign feature ownership
  - Set up the Next.js and FastAPI applications
  - Design the PostgreSQL schema
  - Configure Docker Compose and repository standards

- **Week 2 â€” Accounts and Database:**
  - Implement registration and login
  - Add JWT authentication
  - Create user and interview database models
  - Configure SQLAlchemy and Alembic

- **Week 3 â€” Interview Setup:**
  - Create role, job-description, and experience-level selection
  - Build interview session APIs
  - Generate and store the initial question set

- **Week 4 â€” Typed Interview Flow:**
  - Submit typed responses
  - Generate adaptive follow-up questions
  - Save the interview conversation
  - Complete the first working interview from start to finish

- **Week 5 â€” Scoring and Reports:**
  - Implement the scoring rubric
  - Generate structured feedback
  - Build interview results and history pages
  - Add automated tests for scoring and interview logic

- **Week 6 â€” Voice Integration:**
  - Connect the Deepgram Voice Agent API
  - Stream microphone audio
  - Play interviewer responses
  - Store voice transcripts

- **Week 7 â€” Barge-In and Reliability:**
  - Support interruptions during AI speech
  - Handle denied microphone permissions and lost connections
  - Improve loading, error, and empty states
  - Add end-to-end tests

- **Week 8 â€” Release:**
  - Deploy the application
  - Conduct user testing
  - Fix high-priority issues
  - Finalize documentation and presentation materials

---

## Branching Rules

- **Main Branch:**
  - `main` must remain stable and deployable
  - No direct commits to `main`
  - Changes enter `main` only through an approved pull request

- **Feature Branches:**
  - Create each branch from the latest version of `main`
  - Use the following naming pattern:

    ```text
    type/short_description
    ```

  - Examples:

    ```text
    feature/auth_jwt
    feature/interview_setup
    feature/deepgram_voice
    feature/scoring_report
    fix/voice_reconnect
    test/interview_routes
    ```

- **Creating a Branch:**

  ```bash
  git checkout main
  git pull origin main
  git checkout -b feature/interview_setup
  ```

---

## Development Process

1. Select or receive an assigned issue.
2. Pull the newest version of `main`.
3. Create a focused branch for the feature or fix.
4. Implement and test the change locally.
5. Push the branch to GitHub.
6. Open a pull request into `main`.
7. Address review feedback and wait for approval.

Keep each branch and pull request focused on one feature. Large features should be divided into smaller tasks that can be reviewed independently.

---

## Pull Request Rules

- All code changes must be submitted through a pull request.
- Every pull request must include:
  - A clear explanation of the change
  - A short summary of how it works
  - Testing that was performed
  - Any database or migration changes
  - Any new environment variable names
  - Screenshots or recordings for frontend changes
  - Known limitations or follow-up work
- Tests and automated checks must pass before merging.
- Do not include API keys, passwords, `.env` files, or other secrets.

Example pull request title:

```text
Add experience-level interview setup
```

---

## Review and Merge Process

- At least one teammate must review each pull request.
- The author must respond to requested changes before approval.
- Contributors cannot approve or merge their own pull requests.
- The project manager performs the final merge into `main`.
- Pull requests should be squash merged to keep the commit history readable.
- Urgent fixes still require a pull request and review.

---

## Example Workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/deepgram_voice

# Implement and test the feature

git add .
git commit -m "Add Deepgram voice interview session"
git push origin feature/deepgram_voice
```

Then open a pull request on GitHub, request a review, address feedback, and wait for the project manager to merge the approved change.

---

## Resources

### Everyone Should Review

- [Git and GitHub Basics](https://docs.github.com/en/get-started/using-git/about-git)
- [REST API Concepts](https://developer.mozilla.org/en-US/docs/Glossary/REST)
- [Docker Compose](https://docs.docker.com/compose/intro/compose-application-model/)
- [System Design Basics](https://github.com/donnemartin/system-design-primer)

### Backend

- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [FastAPI JWT Authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Pydantic Documentation](https://docs.pydantic.dev/latest/)
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [Pytest Documentation](https://docs.pytest.org/)

### Frontend and Voice

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TanStack Query Documentation](https://tanstack.com/query/latest/docs/framework/react/overview)
- [Deepgram Voice Agent API](https://developers.deepgram.com/docs/voice-agent)
- [Deepgram Voice Agent Architecture](https://developers.deepgram.com/docs/voice-agent-architecture)
- [Playwright Documentation](https://playwright.dev/docs/intro)

---

## Project Status

Mockwright is currently in active planning and early development. The MVP scope and timeline may be adjusted as the team validates the interview experience.

---

## License

License selection is pending.
