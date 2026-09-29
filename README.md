# StudyMate AI

An AI-powered personalised learning assistant. Upload your lecture
material, and StudyMate extracts the key concepts, generates revision
material from them, marks your answers, and tracks which topics you
actually know.

Final-year BSc Information Technology project, University of Ghana,
Department of Computer Science.

## What it does

- **Ingests** PDF, DOCX, PPTX and plain text/Markdown files, plus notes
  typed straight into the app.
- **Extracts key concepts** from each document automatically.
- **Builds a cumulative knowledge base** per student per course, merging a
  topic taught across several lectures into one entry.
- **Generates** flashcards, multiple choice, fill-in-the-blank,
  short-answer questions and full exam papers — from one lecture or from
  the whole course.
- **Marks** your answers: instantly for multiple choice and fill-in-the-
  blank, and with an AI judge for written answers, which accepts a correct
  answer in your own words.
- **Coaches** you: per-concept mastery, weak-topic detection, and a ranked
  list of what to revise next.
- **Tracks progress** with XP, daily streaks and badges.

Deliberately out of scope: audio/video transcription, plagiarism
detection, LMS integration, non-English material.

## Documentation

- [PROJECT_PLAN.md](./PROJECT_PLAN.md) — scope, tech stack and the
  architecture decisions agreed up front.
- [docs/implementation-notes.md](./docs/implementation-notes.md) — what was
  built, which open questions were settled and how, and the points where
  measurement changed the design.
- [docs/evaluation/](./docs/evaluation/) — usability test protocol, SUS
  questionnaire, and the instructor review rubric for assessment quality.

## Running it

You need Docker and a free Google AI Studio API key
([aistudio.google.com/apikey](https://aistudio.google.com/apikey) — no
billing required).

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`, then:

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:9000 (interactive API docs at `/docs`)

The backend container runs database migrations on startup. A separate
`worker` container handles concept extraction and question generation, so
**both `backend` and `worker` must be running** for uploads to finish
processing.

> The backend is published on host port 9000 rather than 8000 because 8000
> falls inside a Windows-reserved TCP exclusion range on the development
> machine and cannot be bound there.

## Running the tests

Backend, with the stack up:

```bash
docker compose exec backend pytest
```

The suite creates and uses a separate `studymate_test` database, so it
never touches your development data.

Frontend:

```bash
cd frontend
npm install
npm test
```

## Architecture

```
frontend/   React + TypeScript + Vite + Tailwind
backend/    FastAPI
  app/api/            routers: auth, courses, documents, assessments, coach, profile
  app/models/         SQLAlchemy models
  app/services/
    extraction/       per-format text extraction, dispatched by file type
    ai/               AIProvider interface + Gemini adapter
    knowledge_base.py concept de-duplication and merging
    coaching.py       mastery, weak topics, recommendations
    gamification.py   XP, streaks, badges
    grading.py        deterministic marking
  app/workers/        RQ jobs: extraction, generation
  migrations/         Alembic
```

PostgreSQL for data, Redis + RQ for background jobs. Anything that calls a
language model runs in a worker rather than in the request, so uploads and
generation never block the browser — the one exception is marking written
answers, which happens during submission so the student gets feedback in
the same response.

The LLM provider sits behind an `AIProvider` interface with one concrete
adapter, so swapping provider or model is a change in a single file. This
was not hypothetical: the model had to change twice during development as
free-tier availability shifted.

## Project status

Phases 0–6 of the build plan are complete and verified end to end against
the live API. Phase 7's evaluation instruments are prepared; the usability
sessions, instructor review and write-up remain to be carried out.

One known gap: the React pages have no automated tests beyond a smoke
test, and no browser-level testing was possible in the development
environment. See the end of
[docs/implementation-notes.md](./docs/implementation-notes.md).
