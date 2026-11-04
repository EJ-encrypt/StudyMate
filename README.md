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
- **Arcade**: two revision games built from your own material. *Beat the
  Clock* is a timed sprint through your multiple-choice and fill-in-the-blank
  questions, and *Concept Match* is a memory game pairing concepts with their
  meanings.
- **Lecture timetable and reminders**: type your timetable in, or upload a
  photo or PDF of it and the AI reads it. You are reminded an hour before each
  lecture and when it starts. When it ends, you are prompted to upload the
  slides or write down what you learnt, which goes into your notes.
  Reminders arrive as push notifications, by email, or both.

Deliberately out of scope: audio/video transcription, plagiarism
detection, LMS integration, non-English material.

## Documentation

- [PROJECT_PLAN.md](./PROJECT_PLAN.md) — scope, tech stack and the
  architecture decisions agreed up front.
- [docs/implementation-notes.md](./docs/implementation-notes.md) — what was
  built, which open questions were settled and how, and the points where
  measurement changed the design.
- [docs/deployment.md](./docs/deployment.md) — putting it online with
  Vercel and Supabase, step by step.
- [docs/evaluation/](./docs/evaluation/) — usability test protocol, SUS
  questionnaire, and the instructor review rubric for assessment quality.

## Running it

StudyMate is hosted: the web app and API on **Vercel**, the database, sign-in,
file storage and scheduler on **Supabase**, all on free plans. Students only
need the link.

**[docs/deployment.md](./docs/deployment.md)** walks through the whole setup
step by step, from creating the accounts to the first test, plus a
troubleshooting table and how to run it locally.

## Running the tests

Backend (needs a PostgreSQL; `docker compose up -d` starts one):

```bash
cd backend
pip install -r requirements-dev.txt
pytest
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
api/index.py  Vercel entry point: mounts the FastAPI app under /api
frontend/     React + TypeScript + Vite + Tailwind, lucide icons
  public/sw.js        service worker: shows push reminders
backend/      FastAPI
  app/api/            routers: auth, courses, documents, assessments, coach,
                      profile, schedule, notifications/jobs/cron, games
  app/models/         SQLAlchemy models
  app/services/
    extraction/       per-format text extraction, dispatched by file type
    ai/               AIProvider interface, Gemini and Mistral adapters,
                      shared prompts, and the fallback chain
    quantitative.py   spotting maths material, which is transcribed with LaTeX
    knowledge_base.py concept de-duplication and merging
    coaching.py       mastery, weak topics, recommendations
    gamification.py   XP, streaks, badges
    games.py          Beat the Clock and Concept Match rounds and scoring
    reminders.py      which lecture reminders are due, sent exactly once
    notifications.py  web push and email delivery
    storage.py        Supabase Storage (or a local folder in development)
    grading.py        deterministic marking
  app/workers/        jobs: a Postgres-backed queue, extraction, generation
  migrations/         Alembic
supabase/setup.sql    storage bucket and every-minute scheduler
```

Sign-in is Supabase Auth: the browser signs in with Supabase, and the API
only verifies the token it receives, creating the student's StudyMate
profile on their first request. Uploads go straight from the browser to a
private Supabase Storage bucket through a signed URL, because Vercel rejects
request bodies over 4.5MB.

Anything that calls a language model runs as a job rather than inside the
request that asked for it. There is no long-running worker on serverless
hosting, so jobs are rows in a `jobs` table: the browser asks the API to
process its own jobs straight after queueing them, and a Supabase `pg_cron`
schedule calls the API every minute to send due reminders and pick up
anything left over. Jobs are claimed with a lease, so one whose function was
cut off is retried rather than stuck. Marking written answers is the
exception: it happens during submission so the student gets feedback in the
same response.

The LLM provider sits behind an `AIProvider` interface. Two adapters exist
(Gemini and Mistral) and `AI_PROVIDERS` lists them in order: the first serves
requests, the second is tried when it fails. This is not hypothetical
robustness - on a free tier every Gemini model can be rate-limited at once,
and within one provider there is nowhere left to go. Both have free tiers.
An OpenAI adapter existed earlier and was removed: it has no free tier.

Model lists are configuration (`GEMINI_MODELS`, `MISTRAL_MODELS`) so a
retired or misspelled model is fixable without a code change.

Question sets default to as many items as the material supports: at least
20 flashcards or multiple-choice questions, up to 40, written in batches of
20 so a later batch can be told what an earlier one asked. Maths, statistics
and economics material is recognised by course name and symbol density; its
PDFs and photos are transcribed by the AI with equations as LaTeX, its sets
include worked problems, and numeric answers are marked as numbers.

## Project status

Phases 0–6 of the build plan are complete. On top of them, the app now runs
on Vercel and Supabase, and has the Arcade, the lecture timetable with
reminders, and a redesigned interface that works on phones. Phase 7's
evaluation instruments are prepared; the usability sessions, instructor
review and write-up remain to be carried out.

See [docs/implementation-notes.md](./docs/implementation-notes.md) for
what was verified and how.
