# StudyMate AI

An AI-powered personalized learning assistant: upload lecture materials,
get key concepts extracted automatically, generate flashcards/quizzes/exams,
and track per-student mastery with an AI Study Coach.

See [PROJECT_PLAN.md](./PROJECT_PLAN.md) for full scope, tech stack, and
architecture decisions.

## Running locally

```bash
cp .env.example .env
```

Then set `GEMINI_API_KEY` in `.env` to a free Google AI Studio key
(https://aistudio.google.com/apikey, no billing required) so concept
extraction works.

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173

The backend container runs Alembic migrations on startup. A separate
`worker` container runs the RQ job that extracts concepts from uploaded
PDFs, so both `backend` and `worker` need to be up for uploads to finish
processing.

## Running tests

Backend (requires Postgres reachable at `DATABASE_URL`, e.g. via
`docker compose up postgres -d`):

```bash
cd backend
pip install -r requirements.txt
pytest
```

Frontend:

```bash
cd frontend
npm install
npm test
```
