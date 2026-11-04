# Implementation Notes

What was built against [`PROJECT_PLAN.md`](../PROJECT_PLAN.md), and the
decisions that were settled along the way. Written to be cited from the
dissertation's design and evaluation chapters — particularly the points
where a measurement changed the design, since those are the defensible
parts.

## Status against the plan

| Phase | Scope | State |
|---|---|---|
| 0 | Repo scaffold, Docker Compose, DB schema, auth, React shell | Done |
| 1 | Vertical slice: PDF → concepts → Materials | Done |
| 2 | Multi-format ingestion (DOCX, PPTX, typed notes) | Done |
| 3 | Assessment generation, quiz UI, attempt storage | Done |
| 4 | Cumulative knowledge base, cumulative quizzes | Done |
| 5 | AI Study Coach: mastery, weak topics, recommendations | Done |
| 6 | Gamification: XP, streaks, badges, Profile | Done |
| 7 | Testing & evaluation | Instruments prepared; human studies outstanding |
| + | Hosting on Vercel + Supabase, Supabase Auth | Done |
| + | Arcade: Beat the Clock, Concept Match, True or False, Odd One Out, Three Strikes | Done |
| + | Friends, challenges, leaderboards, report and block | Done |
| + | Spaced-repetition flashcards, Coach revision topics with sources, photo notes | Done |
| + | Lecture timetable, AI timetable reading, reminders, after-lecture reflection | Done |
| + | Interface redesign: icons, phone layout, installable app | Done |

Out of scope, as the plan specified: audio/video transcription, plagiarism
detection, LMS integration, non-English support.

## Decisions the plan left open

**AI provider.** Two adapters, chained. Not Claude, as originally costed. The budget line turned
out to be documentation-only, with a standing requirement to use free
tiers, and Anthropic has no sustained free API tier. Google AI Studio's
Gemini does, so the concrete adapter targets Gemini. The provider-agnostic
interface the plan insisted on earned its keep immediately: the model ID
had to change twice, and retry and fallback logic was added, all inside
one file. It later paid off again when a second provider was added.

`AI_PROVIDERS` is an ordered list, tried in turn, because within a single
provider there is eventually nowhere left to go: measured against a live
free-tier key, every Gemini Flash model returned 503 or 429 simultaneously
for minutes at a time. A second provider is the only thing that helps, and it
matters most during a usability session, where a participant who cannot get
past an upload has learned nothing about the interface.

Prompts and grade alignment moved into shared modules rather than being
duplicated per adapter. A student should not get noticeably different
questions because their upload happened to land on the fallback, and the
hard-won details in those prompts - the reference formatting, the
fill-in-the-blank constraint - must not drift apart between copies.

**A free backup provider: Mistral.** OpenAI has no free tier, so in
November 2026 the free alternatives were compared against what StudyMate
actually sends. Groq's free tier allows 6,000 tokens a minute, and one
lecture is about 5,000, so it would fail constantly. OpenRouter's free tier
allows 200 requests a day, with inconsistent structured-output support.
Mistral's free plan allows about 500,000 tokens a minute and 1 billion a
month, and has everything the other adapters rely on: JSON-schema output,
its own embedding model, and image input for timetables. The cost is a
phone-verified sign-up and a training-data setting that has to be switched
off. The adapter talks to the REST API directly with httpx; pydantic
schemas are flattened (references inlined, objects closed) for Mistral's
strict mode. A provider listed in `AI_PROVIDERS` without a key is skipped
with a warning rather than failing on every fallback.

**Lite models only.** On the free tier, `gemini-3.8-flash` was measured
answering 503 and 504 for minutes at a time while the lite models answered in
seconds. Every model in the list costs up to a minute when it fails, so
the list is now the two lite models. The trade-off is some quality on the
reasoning-heavy tasks: plausible wrong options in multiple-choice questions,
judging written answers, and deciding whether two concepts are the same. The
instructor review in Phase 7 should look at these specifically.

**Embeddings cannot fall back silently.** Two embedding models produce
vectors with different geometry and often different dimensions, so a
similarity score between them is meaningless rather than merely imprecise.
Every stored vector therefore records the model that produced it, the chain
exposes `embed_tagged` instead of a plain `embed`, and de-duplication only
compares concepts sharing an embedding model. When a fallback embeds a batch,
the primary's existing concepts simply are not candidates - which can leave a
duplicate, the recoverable direction, instead of merging on a nonsense score.

**The OpenAI adapter was removed.** It was written early from the
published SDK shape but never exercised against the live API, because
OpenAI has no free tier. Mistral replaced it as the second provider. Both
remaining providers take their model lists from configuration
(`GEMINI_MODELS`, `MISTRAL_MODELS`) so a wrong name is fixable without a
code change, which is exactly the failure that occurred with Gemini
mid-project.

**Short-answer grading — LLM-as-judge.** Measured against a fixed question
and model answer, the judge accepted *"stops you storing the same thing
twice so it cant go out of sync"* as equivalent to the model answer, while
rejecting a confidently wrong answer and one that merely restated the
question — 7 of 7 verdicts as intended. Exact matching would have failed
all three correct answers. The cost is latency: roughly ten seconds to mark
three answers, batched into a single call so a submission costs one request.
Quizzes containing no written answers never call the model at all.

**Badge relationships — Badge↔Student.** The proposal's ERD linked Badge to
Course many-to-many with no student junction, which cannot express "this
student earned this badge". Earned badges are therefore keyed to the
student. Badge definitions are a fixed catalogue in code rather than a
table, so there is no definition table to drift from the code that awards
them.

**Course creation — self-service per student.** Students create and own
their own course records. This follows from the plan's decision that the
knowledge base is siloed per student: with no sharing between classmates,
a course is a student's own organising unit, and no lecturer-side
enrolment flow is needed for the prototype.

**pgvector — still not needed.** The plan made it conditional on whether
embeddings were required for de-duplication. They were, and embeddings
turned out to be free-tier available, but a course holds a few hundred
concepts at most, so vectors are stored as JSONB and compared in Python.
That avoided swapping the Postgres image for an extension build. If a
course ever holds tens of thousands of concepts, this is the thing to
revisit.

**Lecturer role — not built.** The proposal's use-case diagram included
lecturer review of generated content, but designed no screens for it. The
role exists on the user record; no lecturer-facing functionality does. The
instructor review in Phase 7 is run offline against
[`docs/evaluation/instructor-review-rubric.md`](./evaluation/instructor-review-rubric.md)
instead, which gets the quality assurance the proposal wanted without
building an unspecified interface.

**Data retention.** Uploaded files live in a private Supabase Storage
bucket, reachable only through short-lived signed URLs issued by the API;
Supabase encrypts its storage at rest. Deleting a course removes its files,
questions and scores, and deleting an account removes everything the
student added. There is no fixed retention period: material stays until
the student deletes it. A deployment holding real student data at scale
would need a written retention policy and a data-protection review first.

## Moving to serverless hosting (November 2026)

The prototype originally ran as five Docker containers (Postgres, Redis, an
RQ worker, the API and the frontend), which is too heavy for the development
laptop and cannot be shared without a tunnel. It now runs on Vercel and
Supabase free tiers. Each part of the old design had to change for a reason
specific to serverless hosting:

**No long-running worker, so the queue moved into Postgres.** Vercel runs
each request as a function that stops when the response is sent, so RQ had
nothing to run on. Jobs are now rows in a `jobs` table, claimed with
`SELECT ... FOR UPDATE SKIP LOCKED` and a six-minute lease. The browser asks
the API to run its own jobs straight after queueing them, and a Supabase
`pg_cron` schedule calls the API every minute as a sweep. A function cut off
mid-job loses its lease and the job is retried. After three attempts the
student sees a failure with a retry button rather than a spinner that never
ends.

**Vercel's 4.5MB request limit, so uploads bypass the API.** Lecture slides
often exceed it. The API issues a signed upload URL per file, the browser
uploads directly to a private Supabase Storage bucket, and the API then
records the documents. The storage path is always derived on the server from
ids it controls, so a student can only register files under their own prefix.

**Supabase Auth instead of in-house passwords.** Sign-up, email confirmation
and password reset are handled by Supabase. The API verifies the access
token (asymmetric keys via JWKS, or the legacy shared secret) and creates the
StudyMate profile on a student's first request, keyed by the Supabase user
id. Tokens for another audience, including the anon key itself, are rejected.

**Supabase publishes every table, so row-level security is on everywhere.**
Supabase's REST API exposes the `public` schema to anyone holding the anon
key, which ships in the frontend bundle. Without row-level security, every
student's data would be readable over the internet. Migration `0011` enables
RLS on every table with no policies. The API connects as the table owner,
which bypasses RLS, so it is unaffected.

**Vercel's free scheduler runs once a day,** which cannot send "an hour
before your lecture". `pg_cron` in Supabase calls the API every minute
instead.

## Games and reminders: decisions

**Games use existing material and no model calls.** Beat the Clock draws its
questions from the student's completed multiple-choice and fill-in-the-blank
sets. Fill-in-the-blank items become four buttons, with decoys taken from
other answers and concept names in the same course. Concept Match uses the
course knowledge base, with the concept's name masked out of its clue. A
round starts instantly and costs nothing against the AI quota. Scoring is
recomputed on the server from the submitted answers. Answer times come from
the browser and are clamped, which is enough for a personal-best table.

**Only one game counts towards mastery.** Answering a timed question is
evidence of knowing a concept, so Beat the Clock answers move mastery
exactly as quiz answers do. Matching a name to its definition is
recognition, a weaker signal, so Concept Match earns XP but leaves mastery
alone.

**Reminders are idempotent by construction.** A reminder stays due for a
ten-minute window, so a late or skipped tick still sends it. A unique
`(slot, date, kind)` row is claimed before sending, so overlapping ticks can
never send it twice. Times are stored as wall-clock times in the student's
time zone, which the browser reports at onboarding, so 09:00 means nine
o'clock where the student is.

**A timetable read by the AI is a proposal, not data.** A misread time would
mistime every reminder for the semester, so nothing is saved until the
student has reviewed and edited the rows. Unreadable rows are dropped rather
than guessed.

**Two notification channels, because neither reaches everyone.** Web push is
instant but an iPhone only receives it from the home-screen app. Email
(SMTP, e.g. Gmail) reaches everyone but is easier to miss.

## Where measurement changed the design

These are the parts worth defending in a viva, because the obvious approach
was tried and shown to be wrong.

**Concept de-duplication cannot use a similarity threshold.** The intuitive
design — merge two concepts when their embeddings are similar enough —
fails on real material. Embedding name and summary with `gemini-embedding-2`:

| Pair | Similarity | Must |
|---|---|---|
| "TLB" / "Translation Lookaside Buffer" | 0.850 | merge |
| "Second Normal Form (2NF)" / "Third Normal Form (3NF)" | 0.852 | **not** merge |

No threshold separates those. On names alone it was far worse — 2NF/3NF
scored 0.956, above every pair that genuinely should merge. So similarity
is used only to sort candidates into three bands: confidently the same,
confidently different, and an ambiguous middle that the model adjudicates.
Every uncertain case defaults to not merging, because a missed merge leaves
a harmless duplicate whereas a wrong merge silently deletes a concept from
the student's knowledge base.

**Mastery is a moving average, not a percentage.** A plain correct/total
ratio holds a student back indefinitely for early wrong answers made before
they learned the topic. An exponential moving average (rate 0.4) lets a
student who has since learned something climb out of "weak", while a
minimum attempt count prevents one lucky guess from reading as mastery.
"Not practised" is a distinct state from "practised badly", because they
call for different advice.

**Recommendations are computed, not generated.** Ranking weak concepts
first, then unpractised, then developing, is deterministic, instant, free,
and explainable to the student. It also keeps the Coach page off the
free-tier quota that generation and marking already compete for.

## Bugs that only appeared when run for real

Recorded because they are evidence for the evaluation chapter's argument
that a working test suite is not the same as a working system. Each of
these passed every unit test.

1. **Enum persistence mismatch.** SQLAlchemy stores enum *names* by
   default; the migrations created Postgres types with lowercase *values*.
   Every user and document insert failed. Fixed with `values_callable`.
2. **Duplicate `CREATE TYPE`.** `create_table()` auto-emits `CREATE TYPE`
   for enum columns, colliding with the explicit `.create()`, so the first
   migration crashed on a clean database.
3. **`passlib` versus modern `bcrypt`.** `passlib` 1.7.4 probes bcrypt with
   an over-length password that bcrypt 5.x rejects outright, breaking
   registration. Replaced with the `bcrypt` library directly.
4. **Path traversal in uploads.** Filenames and note titles were
   interpolated into storage paths, so `../../../evil.pdf` escaped the
   storage directory. Names are now reduced to a bare safe filename, and
   the extension is validated *after* sanitising so it matches what the
   worker later dispatches on.
5. **Gemini rejects response schemas containing defaults.** Two fields with
   defaults failed 100% of generation calls. A test now walks every schema
   for defaults.
6. **Reference echo in batched marking.** The grading prompt wrapped each
   answer's id as `[id]`, so the model echoed the brackets back as part of
   the id and every lookup missed. The guard against mis-attribution then
   reported every answer as unmarkable — correct behaviour, useless
   outcome. Matching now tolerates decoration and falls back to order.
7. **Knowledge-base sync ordering.** The merge ran after the document was
   marked complete, so a student could see "Done" while the course
   knowledge base was still missing that lecture.
8. **Badge double-award.** Badges are awarded read-then-insert, and with
   `autoflush` off the pending row was invisible to the next check,
   violating the unique constraint.

9. **Mastery double-insert.** The same autoflush problem as the badges,
   in mastery tracking: two answers about the same concept in one
   submission, for a student with no record on it yet, both tried to create
   the record, and the submission failed. A quiz with two questions on one
   topic could trigger it. The first Beat the Clock test found it.
10. **The embedding API changed underneath the knowledge base.** Measured
    in November 2026, `gemini-embedding-2` returned *one* vector for a list
    of texts, combining them into a single input. The merge code paired
    concepts with vectors using `zip`, which stops at the shorter list
    without complaint, so every upload kept its first concept and silently
    dropped the rest. Ten concepts were extracted and one reached the
    knowledge base. Nothing failed and nothing was logged, and every unit
    test passed, because the tests stub the embedding call. Each text is now
    sent as its own content item, and a count mismatch is an error. Found
    only by running a real upload end to end.
11. **Unbounded model calls.** The Gemini SDK sets no request timeout. On a
    congested free-tier model, single calls were measured taking over four
    minutes, longer than a Vercel function may run. Requests now time out
    after 60 seconds, and a timed-out model is skipped for the next one
    rather than retried. The course overview, the slowest call and the least
    important, moved into a separate job.

**Free-tier reliability deserves its own mention.** Measured against a live
key, most Gemini Flash models returned 503 "high demand" simultaneously,
while a lite variant answered normally; one raised a bare `ConnectionError`
rather than an API error. A single fixed model failed two of three uploads.
Generation therefore retries transient failures and falls back through a
list of models. Any evaluation session should expect occasional rate-limit
failures and record them as infrastructure events, not usability defects.

## Verification performed

- 268 automated backend tests, run against live PostgreSQL, including the
  job queue, Supabase token verification, the upload flow, games,
  timetable reading, reminder timing and idempotency, and the Mistral
  adapter against recorded API responses.
- Frontend type-checks and builds clean; 50 component and unit tests,
  including the navigation, the guided tour, the Concept Match game, adding
  courses, the offline notice and the Coach revision topics.
- The full student journey, run through the Vercel entry point against a
  fresh database migrated from scratch, with real Gemini calls: sign-up,
  upload, concept extraction, knowledge base, MCQ generation, both games,
  AI timetable reading from an image, reflection, and the scheduler tick.
- Every phase exercised end to end against the live Gemini API: multi-format
  upload, concept extraction, all five assessment kinds, deterministic and
  LLM marking, cumulative de-duplication across two overlapping lectures,
  mastery movement in both directions, and badge awarding.

**Not verified automatically: the interface end to end.** The component
tests render pages and click through them in a simulated browser, but no
test drives the real site in a real browser across a whole journey. The
interface has been exercised by hand on a laptop and an iPhone throughout
development; the usability sessions in Phase 7 are its first structured
test with other students. Browser-driven end-to-end tests would be the
highest-value addition to this work.
