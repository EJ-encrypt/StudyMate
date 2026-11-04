# StudyMate AI

An AI-powered personalised learning assistant. Upload your lecture
material, and StudyMate extracts the key concepts, generates revision
material from them, marks your answers, and tracks which topics you
actually know.

Final-year BSc Information Technology project, University of Ghana,
Department of Computer Science.

## What it does

- **Ingests** PDF, DOCX, PPTX and plain text/Markdown files, notes typed
  straight into the app, and photos of handwritten notes (turned into a PDF
  on the phone and read by the AI, handwriting included).
- **Extracts key concepts** from each document automatically, remembering
  the page or slide each one came from.
- **Builds a cumulative knowledge base** per student per course, merging a
  topic taught across several lectures into one entry, with a running
  summary of the course so far.
- **Generates** flashcards, multiple choice, fill-in-the-blank,
  short-answer questions and full exam papers, from one lecture or from
  the whole course.
- **Marks** your answers: instantly for multiple choice and fill-in-the-
  blank, and with an AI judge for written answers, which accepts a correct
  answer in your own words.
- **Spaced repetition**: flashcards you mark "Still learning" come back
  after 1, 3, 7, 14 and 30 days (Leitner boxes).
- **Coaches** you: per-concept mastery, weak-topic detection, and up to five
  topics to revise next. Each topic opens to its concepts, where each is
  explained in your material (page or slide), and how they fit together.
- **Tracks progress** with XP, daily streaks, badges and a daily goal.
- **Arcade**: five revision games built from your own material: Beat the
  Clock, Concept Match, True or False, Odd One Out and Three Strikes.
- **Leaderboard**: friends by username, weekly and all-time XP, challenges
  to beat a friend's score on the same round, an opt-in board for your
  programme, and report/block.
- **Levels and semesters**: courses are kept per level and semester, so
  earlier levels stay available, and the Study Engine, Coach and Arcade can
  revise any of them.
- **Lecture timetable and reminders**: type your timetable in, or upload a
  photo or PDF of it and the AI reads it. You are reminded an hour before each
  lecture and when it starts. When it ends, you are prompted to upload the
  slides or write down what you learnt, which goes into your notes.
  Reminders arrive as push notifications, by email, or both.
- **Works on phones** as an installable web app, with a guided tour, offline
  messages and daily limits on AI use so the free tiers last.

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
    games.py, arcade.py  the five Arcade games: rounds and scoring
    review.py         spaced-repetition flashcard reviews
    social.py         friends, challenges, leaderboards, blocks
    sources.py        which page or slide a concept came from
    limits.py         daily AI limits
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

All phases of the build plan are complete and the app is live at
https://studymate-alpha-fawn.vercel.app. Beyond the plan it has the Arcade,
friends and leaderboards, the lecture timetable with reminders, spaced
repetition and an interface that works on phones. The evaluation
instruments in [docs/evaluation/](./docs/evaluation/) are prepared; the
usability sessions and instructor review are the remaining Phase 7 work.

See [docs/implementation-notes.md](./docs/implementation-notes.md) for
what was verified and how.
