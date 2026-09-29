# StudyMate AI — Usability Test Protocol

A script for running a moderated usability session with one student at a
time. Everything the moderator says aloud is in quotes; everything else is
an instruction to the moderator.

**Target:** 5–8 undergraduate participants who are currently taking at
least one lecture-based course. Five is enough to surface most usability
problems; more mainly adds confidence to the SUS score.

**Duration:** 30–40 minutes per participant.

**You will need:** a laptop running StudyMate with a working
`GEMINI_API_KEY`, two or three real lecture PDFs the participant has not
seen before, a printed or on-screen copy of
[`sus-questionnaire.md`](./sus-questionnaire.md), and a way to take notes.

---

## Before the participant arrives

1. Start the stack (`docker compose up -d`) and confirm the app loads at
   http://localhost:5173.
2. Create a **fresh account** for the session. Do not reuse an account —
   existing XP, badges and mastery would change what the participant sees
   and invalidate the first-run experience.
3. Have the lecture PDFs ready in an obvious folder.
4. Check your free-tier quota has headroom. Generation and marking both
   call the model, and a session can use a dozen calls or more. If the
   model is rate-limited mid-session the participant will see failures
   that are not usability problems — note it if it happens, and say so in
   the write-up rather than counting it against the interface.

## Introduction (read aloud)

> "Thanks for helping. This is a study tool I've built that takes lecture
> material and turns it into revision questions. I'm testing the software,
> not you — if something is confusing, that's a problem with what I've
> built, and that's exactly what I need to find.
>
> Please think aloud as you go: say what you're looking at, what you
> expect to happen, and what you're trying to do. If you get stuck, say
> so — I may not help immediately, because where people get stuck is the
> useful part.
>
> You can stop at any time, and nothing you do here affects you in any
> way. May I take notes while you work?"

Confirm consent before continuing. If recording, ask explicitly and
separately.

---

## Tasks

Give the participant the task, then stop talking. Do not point at the
screen. Record: whether they completed it unaided, how long it took,
where they hesitated, and their exact words when confused.

### Task 1 — Get in (target: under 2 minutes)
> "Create yourself an account and sign in."

Watch for: whether the password rules are discoverable before submitting
rather than only on error.

### Task 2 — Add a course and upload a lecture (target: under 3 minutes)
> "You've just come out of a lecture. Get this PDF into the app so you
> can revise from it."

Watch for: whether they find course creation without prompting, whether
they understand they must pick a course first, and whether they can tell
that processing is happening and roughly how long it will take.

### Task 3 — Find out what was extracted (target: under 2 minutes)
> "Show me what the app got out of that lecture."

Watch for: whether they navigate to Materials unaided, and whether
"concepts" means anything to them without explanation.

### Task 4 — Revise with flashcards (target: under 3 minutes)
> "Use the app to revise this lecture with flashcards."

Watch for: whether they realise flashcards must be generated first, and
whether the show/hide answer interaction is obvious.

### Task 5 — Take a quiz and interpret the result (target: under 5 minutes)
> "Test yourself on this lecture with multiple-choice questions, and then
> tell me how you did."

Deliberately let them answer some incorrectly if they wish. Watch for:
whether they understand the score, whether the correct answer and
explanation are found without help, and whether they expect to be able to
retake it.

### Task 6 — Written answers (target: under 5 minutes)
> "Now try the short-answer questions."

This is the slowest path in the app — marking calls the model and can
take ten seconds or more. Watch for: whether they think it has frozen,
and whether they consider the marking fair when their wording differs
from the model answer. **Ask directly:** *"Did you agree with how that
was marked?"* Their answer is the most important data in the session.

### Task 7 — A second lecture, and the cumulative view (target: under 4 minutes)
> "Upload this second lecture too, then show me everything you've
> covered in this course so far."

Watch for: whether they notice that topics appearing in both lectures are
listed once, and whether that surprises or pleases them.

### Task 8 — Find out what to revise (target: under 3 minutes)
> "Based on everything you've done, what should you revise next?"

Watch for: whether they reach the Coach page unaided, and whether
"Needs work" / "Developing" / "Not practised" are interpreted the way
they are meant.

### Task 9 — Progress (target: under 2 minutes)
> "Find out what you've earned so far."

Watch for: whether XP, streaks and badges feel motivating or irrelevant.
Ask which, if any, they would actually care about.

---

## Closing questions

Ask all of these, and write down answers verbatim where you can.

1. "What was the most useful thing the app did for you?"
2. "What was the most annoying or confusing part?"
3. "Were the questions it generated any good? Were any of them wrong?"
4. "Would you use this to revise for a real exam? Why, or why not?"
5. "If you could change one thing, what would it be?"

Then administer the SUS questionnaire. Ask the participant to answer
without discussion — discussing first biases the score.

---

## Recording results

For each participant log: ID (P1, P2, …), task completion (unaided /
with a hint / failed), time per task, errors observed, verbatim quotes,
SUS score, and any model failure (rate limit, refused generation) that
affected the session.

Report task success as a rate per task rather than an average across
tasks — a single task that everyone fails is a specific fixable problem,
and averaging hides it.
