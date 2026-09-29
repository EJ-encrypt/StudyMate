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

**Embeddings cannot fall back silently.** Two embedding models produce
vectors with different geometry and often different dimensions, so a
similarity score between them is meaningless rather than merely imprecise.
Every stored vector therefore records the model that produced it, the chain
exposes `embed_tagged` instead of a plain `embed`, and de-duplication only
compares concepts sharing an embedding model. When a fallback embeds a batch,
the primary's existing concepts simply are not candidates - which can leave a
duplicate, the recoverable direction, instead of merging on a nonsense score.

**The OpenAI adapter is unverified against the live API.** No key was
available. It is written from the published SDK shape and its call was
confirmed to reach OpenAI's servers - a deliberately invalid key returned a
structured 401 rather than a client-side type error, so the request is
well-formed - but neither the model IDs nor the response parsing has been
exercised for real. Both providers take their model lists from configuration
(`GEMINI_MODELS`, `OPENAI_MODELS`) so a wrong name is fixable without a code
change, which is exactly the failure that occurred with Gemini mid-project.

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

**Data retention.** Uploaded files are stored on a local volume and are not
encrypted at rest. This is adequate for a prototype evaluated on synthetic
and volunteered material, and is **not** adequate for real student data at
scale. Anyone extending this should treat encryption at rest and a
retention policy as prerequisites, not enhancements.

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

**Free-tier reliability deserves its own mention.** Measured against a live
key, most Gemini Flash models returned 503 "high demand" simultaneously,
while a lite variant answered normally; one raised a bare `ConnectionError`
rather than an API error. A single fixed model failed two of three uploads.
Generation therefore retries transient failures and falls back through a
list of models. Any evaluation session should expect occasional rate-limit
failures and record them as infrastructure events, not usability defects.

## Verification performed

- 113 automated backend tests, run against live PostgreSQL.
- Frontend builds clean and its test suite passes.
- Every phase exercised end to end against the live Gemini API: multi-format
  upload, concept extraction, all five assessment kinds, deterministic and
  LLM marking, cumulative de-duplication across two overlapping lectures,
  mastery movement in both directions, and badge awarding.

**Not verified: the interface itself.** Every check above is at API, worker,
database or build level. No automated browser driving was available in the
development environment, so no test confirms that the pages behave
correctly when clicked. The usability sessions in Phase 7 are the first
real exercise of the UI, which is a genuine gap — a component test suite
for the React pages would be the highest-value addition to this work.
