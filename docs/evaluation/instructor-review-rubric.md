# Instructor Review — Generated Assessment Quality

Usability testing tells you whether students can operate StudyMate. It does
not tell you whether the questions it generates are any *good* — a student
cannot reliably judge whether a question about their own lecture is
accurate, well-formed, or fair. That requires someone who knows the
material. This rubric is for that reviewer.

**Reviewer:** a lecturer or teaching assistant who teaches the course the
material comes from.

**What to prepare:** generate, from real lecture material for their course,
one set of each kind — flashcards, multiple choice, fill-in-the-blank,
short answer — plus one exam paper. Around 30–40 items total is enough to
see patterns without asking for an unreasonable amount of the reviewer's
time. Export or screenshot them **with the correct answers shown**, since
the app deliberately hides answers from students until submission.

Give the reviewer the source lecture material alongside the questions.
Several criteria below cannot be judged without it.

---

## Per-item rating

For each item, the reviewer marks one rating and adds a comment where the
rating is not "Good".

| Rating | Meaning |
|---|---|
| **Good** | Accurate, clearly worded, and fit to use as-is |
| **Minor issue** | Usable after a small edit (awkward phrasing, imprecise wording) |
| **Flawed** | Not usable as written (ambiguous, trivially guessable, badly scoped) |
| **Wrong** | Factually incorrect, or the marked answer is not correct |

The distinction that matters most is **Flawed** versus **Wrong**. A flawed
question wastes a student's time; a wrong one actively teaches them
something false. Report those two counts separately — never merge them
into a single "problem" figure.

---

## Criteria

Rate each item against these, and note which criterion failed when the
rating is not "Good".

1. **Factual accuracy** — Is the content correct, and is the marked answer
   actually the right one?
2. **Grounding in the source** — Is it answerable from the supplied
   material, or has the model introduced outside knowledge? Flag anything
   the lecture does not cover, even where it is true.
3. **Unambiguity** — Is there exactly one defensible answer? For fill-in-
   the-blank, does enough of the sentence remain to make the missing term
   determinate?
4. **Distractor quality (MCQ only)** — Are the wrong options plausible?
   Options that are obviously absurd, or a correct answer noticeably
   longer or more detailed than the rest, make the question guessable
   without knowing the material.
5. **Cognitive level** — Does it require understanding, or only matching
   a remembered string? A set that is entirely recall is a legitimate
   finding worth reporting.
6. **Model answer adequacy (short answer only)** — Is the model answer
   something a competent student could reasonably produce, and does the
   stated key point list capture what actually deserves credit?
7. **Coverage** — Taken as a whole, does the set cover the material's main
   ideas, or does it over-weight the beginning of the document and
   under-cover the rest?

---

## Marking fairness (short answer)

Short answers are marked by a language model rather than by string
comparison, so its judgement needs checking directly. Prepare, for three
or four short-answer questions, a spread of student answers:

- one matching the model answer closely
- one correct but **worded quite differently**, informally, or more briefly
- one that is partially correct, missing a key point
- one that is confidently wrong
- one that merely restates the question

Run each through the app and record what it decided. Ask the reviewer to
mark the same answers independently, then compare.

| Question | Answer type | Reviewer's mark | StudyMate's mark | Agree? | Reviewer comment |
|---|---|---|---|---|---|
| | close paraphrase | | | | |
| | loose paraphrase | | | | |
| | partially correct | | | | |
| | confidently wrong | | | | |
| | restates question | | | | |

Report agreement as a rate, and describe the **direction** of any
disagreement. Marking too leniently and marking too harshly are different
failures with different consequences for a student relying on the tool,
and a single agreement percentage conceals which is happening.

---

## Summary to collect

| Measure | Result |
|---|---|
| Items reviewed | |
| Good | |
| Minor issue | |
| Flawed | |
| **Wrong (factually incorrect)** | |
| Most common failure criterion | |
| Short-answer marking agreement | |
| Direction of marking disagreement | lenient / harsh / mixed |

Closing questions for the reviewer:

1. "Would you be willing to set any of these for your own students, as-is
   or lightly edited?"
2. "Is there any kind of question here you would consider actively
   misleading?"
3. "Does the set as a whole reflect what you would want a student
   revising this lecture to know?"
