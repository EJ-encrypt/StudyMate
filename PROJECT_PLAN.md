# StudyMate AI — Project Plan

Source: `Project_Proposal.docx` (BSc IT final-year project, University of Ghana,
Dept. of Computer Science — "An AI-Powered Personalized Learning Assistant for
Automated Knowledge Extraction, Assessment Generation, and Student Performance
Improvement"). This document captures the plan agreed before any code was
written, so a fresh session (e.g. local Claude Code in VS Code) has full
context without re-deriving it.

## 1. Scope & Core Features

Single-semester prototype (Jun–Sep 2026, ~4 months incl. write-up), solo
developer. Budget: GHS 2,600 total (~$170), of which only GHS 800 (~$50–55)
is for cloud/API costs for the *entire semester* — this is the tightest
constraint on the AI/NLP design.

Core features:
- **Multi-format ingestion**: PDF, DOCX, PPTX, typed notes.
- **NLP concept extraction**: pulls key concepts out of each uploaded
  lecture document.
- **Assessment generation**: summaries, flashcards, MCQ, fill-in-the-blank,
  short-answer, full exam papers.
- **Cumulative, per-student, course-specific knowledge base** — built
  incrementally from all materials *that student* uploads for a course
  over the semester (see §3, decision on KB privacy).
- **AI Study Coach**: tracks mastery per student per concept, surfaces
  weakest topics, gives revision recommendations.
- **Gamification**: streaks, XP, badges, challenges.
- **Web dashboard**: nav is Upload / Materials / Coach / Profile (from the
  proposal's wireframes), navy/gold theme.
- **Lecturer role (optional)**: can review generated assessments for
  quality — present in the proposal's use-case diagram, but no
  lecturer-facing screens were designed. Depth still undecided (see §4).

Explicitly out of scope: audio/video transcription, plagiarism detection,
LMS integration, non-English support.

## 2. Tech Stack (agreed)

| Layer | Choice |
|---|---|
| Backend | **FastAPI** (Python) |
| Frontend | **React + TypeScript + Vite + Tailwind** |
| Database | **PostgreSQL** (+ `pgvector` if concept de-dup via embeddings is needed) |
| Extraction | `pdfplumber`/`PyMuPDF` (PDF), `python-docx` (DOCX), `python-pptx` (PPTX) |
| NLP/Generation | spaCy for cheap keyword/entity pre-filtering + a swappable LLM provider for structured extraction/generation (see below) |
| Short-answer grading | Not yet decided — embedding similarity vs. LLM-as-judge (see §4) |
| Background jobs | **RQ + Redis** (simpler ops than Celery for a solo project) |
| File storage | Local volume for dev; Cloudflare R2 or Supabase Storage free tier for hosted prototype |
| Auth | JWT email/password (no SSO/LMS integration in scope) |
| Deployment | Docker Compose locally; Render/Railway free tier |
| Testing | pytest (backend), Vitest + RTL (frontend) |

### AI provider: build provider-agnostic

Decision: don't lock in a provider yet. Define an `AIProvider` interface in
`services/ai/` (`extract_concepts`, `generate_content`, `grade_short_answer`)
with one concrete adapter to start (pick the cheapest viable option once
Phase 1's vertical slice shows real cost/quality numbers). Swapping
providers later should be a one-file change, not a rewrite.

### Project structure (monorepo)

```
studymate/
  backend/
    app/
      api/            # routers: auth, courses, documents, concepts, quizzes, coach, gamification
      models/          # SQLAlchemy models
      schemas/          # Pydantic
      services/
        extraction/     # pdf.py, docx.py, pptx.py, notes.py
        nlp/            # concept_extraction.py, embeddings.py
        ai/              # AIProvider interface + adapters
        generation/      # summaries.py, flashcards.py, questions.py, exams.py
        coaching/        # mastery.py, recommendations.py
        gamification/    # streaks.py, badges.py, xp.py
      workers/          # RQ job definitions
      db/               # session, Alembic migrations
    tests/
  frontend/
    src/
      pages/            # Upload, Materials, Coach, Profile, Quiz
      components/
      api/              # typed client
  docker-compose.yml
```

## 3. Key Decisions Made

1. **AI provider**: provider-agnostic adapter now, pick a concrete provider
   after Phase 1 proves cost/quality.
2. **Knowledge-base privacy model**: **fully siloed per student.** The
   proposal's ERD diagram tied uploaded documents to `Course` directly
   (implying a knowledge base shared across every student in a course), but
   the proposal's own scope text (§1.8) already described it as "a
   cumulative... knowledge base built incrementally from all materials **a
   student** uploads" — i.e. per-student. We're going with the per-student
   reading: no sharing between classmates. `LectureDocument` and
   `KnowledgeConcept` key off `(StudentID, CourseID)`, not `CourseID` alone.
   "Cumulative" means cumulative across *that student's* own uploads over
   the semester.
3. **Backend framework**: FastAPI (over the proposal's Django/Node
   suggestions) — async-friendly for LLM calls, lightweight for an
   API-first product with a separate React frontend.

## 4. Open Items Still to Decide

These weren't blocking enough to hold up starting, but should be settled
before the relevant phase:

- **Lecturer role depth**: is lecturer review of generated content in-scope
  for the prototype, or deferred? No lecturer screens exist yet.
- **Short-answer/exam auto-grading approach**: exact-match, keyword overlap,
  embedding similarity, or LLM-as-judge. Affects cost and UX (instant vs.
  delayed feedback). Needed before Phase 3.
- **Badge↔Course relationship**: the proposal's ERD shows Badge↔Course as
  many-to-many, which looks like it should be Badge↔Student (earned
  badges) instead — there's no Student–Badge junction in the diagram.
  Confirm before building the gamification schema (Phase 6).
- **"Review for accuracy" workflow** (mentioned in the proposal's Ethics
  §3.7): no defined owner/process — self-review, optional lecturer flow, or
  deferred?
- **Data retention/security specifics**: "stored securely" isn't
  actionable on its own; need a stance on encryption-at-rest and how long
  uploaded material/student data is kept, especially once real students'
  data is involved in usability testing.
- **Course creation/enrollment flow**: who creates a `Course` record, and
  how does a student join one? Not defined in the proposal.

## 5. Phased Build Plan

Ordered to get a thin end-to-end slice working early (de-risking the LLM
cost/quality question in week 2, not week 8) rather than building all of
extraction before any generation or UI exists.

- **Phase 0 — Foundation** (~1 wk): repo scaffold, Docker Compose, DB
  schema/migrations, auth, React shell with the Upload/Materials/Coach/
  Profile nav.
- **Phase 1 — Vertical slice** (~1–2 wks): upload one PDF → extract text →
  LLM extracts ~10 concepts → show them in Materials. Proves the whole
  pipeline and answers the provider cost/quality question for real.
- **Phase 2 — Multi-format ingestion** (~1 wk): add DOCX, PPTX, typed notes.
- **Phase 3 — Assessment generation** (~2 wks): flashcards/MCQ/fill-in-blank
  first (more deterministic), then short-answer/exams once grading
  (open item above) is settled. Quiz-taking UI + attempt storage.
- **Phase 4 — Cumulative knowledge base** (~1 wk): aggregate + de-dupe
  concepts across a student's documents in a course; cumulative quizzes.
- **Phase 5 — AI Study Coach** (~1–2 wks): mastery calc, weak-topic
  detection, recommendations, Coach dashboard.
- **Phase 6 — Gamification** (~1 wk): streaks, XP, badges, Profile page.
- **Phase 7 — Testing & evaluation** (~2–3 wks): usability testing,
  instructor review, SUS survey, report writing.

## 6. Working Environment Note

Coding for this project happens in a **local Claude Code session in VS
Code**, not in the cloud session that produced this plan. Pull this branch
into your local project folder, open it in VS Code, and start a local
Claude Code session there — point it at this file for full context before
starting Phase 0.
