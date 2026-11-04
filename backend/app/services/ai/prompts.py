"""Prompt text, shared by every provider adapter.

Kept out of the adapters so the wording is identical whichever provider
serves a request. That matters for fallback: a student should not get
noticeably different questions because their upload happened to land on the
second provider. Several of these carry hard-won detail - the reference
formatting and the fill-in-the-blank constraint both exist because of
specific observed failures - and duplicating them per adapter would let them
drift apart.
"""

from app.services.ai.base import ItemKind, ShortAnswerSubmission

# About 15K tokens: a long lecture deck fits whole, and both providers' free
# tiers take it comfortably (Gemini's context is 1M, Mistral Small's 128K).
# 20K, the earlier limit, cut off the second half of longer slide decks, so
# every question came from the first few topics.
MAX_INPUT_CHARS = 60000

# Every kind gets these. They target what made earlier sets easy to game:
# the right option was the longest and most qualified one, distractors were
# obviously from another topic, and most questions only asked for a
# definition back.
_QUALITY_RULES = (
    "Make the set genuinely test understanding:\n"
    "- Spread the items across the whole material, not just its opening topics.\n"
    "- At most a quarter of the items may simply ask for a definition. Write the "
    "rest as application to a short scenario or example, comparison of two ideas, "
    "cause and effect, spotting an error, ordering steps, or predicting an outcome.\n"
    "- Never let the wording give the answer away: the question must not repeat a "
    "distinctive word from the answer, and grammar (a/an, singular/plural) must not "
    "point to it.\n"
    "- No two items may test the same fact in the same way.\n"
)

ITEM_INSTRUCTIONS = {
    ItemKind.FLASHCARD: (
        "Write {count} flashcards as term/definition pairs. 'question' is the term, "
        "name, formula or rule - at most eight words. 'answer' is its definition or "
        "meaning in one or two sentences that do NOT contain the term itself, so the "
        "card works in both directions: the student will sometimes see the term and "
        "recall the definition, and sometimes see the definition and recall the term. "
        "Leave 'options' empty."
    ),
    ItemKind.MCQ: (
        "Write {count} multiple-choice questions. 'question' is the stem, 'options' "
        "holds exactly four distinct answer choices, and 'answer' repeats the correct "
        "option verbatim. Use 'explanation' to say briefly why the answer is right and "
        "why the most tempting wrong option is wrong.\n"
        "The wrong options matter as much as the right one:\n"
        "- Each must be a real misconception or a near miss a student who half-knows "
        "the topic would pick, drawn from the same material and the same category as "
        "the answer (another term from this lecture, a neighbouring step, a related "
        "value).\n"
        "- All four options must have the same grammatical form and a similar length "
        "and level of detail. The correct option must NOT be the longest, the most "
        "qualified, or the only one that is precise.\n"
        "- Never use 'All of the above', 'None of the above', joke options, or options "
        "that are obviously off-topic."
    ),
    ItemKind.SHORT_ANSWER: (
        "Write {count} short-answer questions. 'question' asks for an explanation a "
        "student can give in one to three sentences, 'answer' is the model answer "
        "marking should accept, and 'explanation' notes the key points that must "
        "appear for the answer to count. Prefer 'why', 'how' and 'what would happen "
        "if' questions over 'what is'. Leave 'options' empty."
    ),
    ItemKind.FILL_BLANK: (
        "Write {count} fill-in-the-blank questions. 'question' is a sentence with one "
        "missing term replaced by '_____', and 'answer' is only that term - one or two "
        "words, no punctuation. The blank must hide a meaningful piece of terminology "
        "the student should recall, never a symbol, operator or filler word, and enough "
        "of the sentence must remain for the answer to be unambiguous. Write 'a(n)' "
        "rather than 'a' or 'an' before a blank. Leave 'options' empty."
    ),
}

# Added for maths, statistics, economics and similar material, where testing
# recall of definitions misses the point: the skill is applying a method.
_QUANTITATIVE_RULES = (
    "This is quantitative material. Write all mathematics in LaTeX: $...$ inline, "
    "$$...$$ for a displayed equation. Inside JSON, escape every backslash (\\\\frac).\n"
    "At least half of the items must be worked problems: set fresh numbers or a "
    "new function and ask for a result using a method from the material.\n"
    "Before writing 'answer', work the problem out step by step in 'working'. "
    "'answer' must agree with 'working'.\n"
    "For multiple choice, each wrong option must be the result of one specific, "
    "common mistake - a sign error, a wrong formula, a skipped step, a units or "
    "off-by-one slip - so it looks right to a student who applies the method badly.\n"
    "For fill in the blank on a calculation, the answer is the number alone: an "
    "integer, or a decimal rounded to two places.\n"
)


def concept_extraction_prompt(text: str, max_concepts: int, quantitative: bool = False) -> str:
    maths = (
        " Where a concept is a formula, theorem or method, include the formula in "
        "the summary, written in LaTeX between $ signs."
        if quantitative
        else ""
    )
    return (
        f"Extract up to {max_concepts} key academic concepts from this lecture "
        "material, covering all of it rather than only its opening. For each concept "
        f"give a short name and a one-sentence summary of what it means.{maths}"
        f"\n\n{text[:MAX_INPUT_CHARS]}"
    )


def generation_prompt(
    source_text: str,
    kind: ItemKind,
    count: int,
    concepts: list[str] | None = None,
    quantitative: bool = False,
    avoid: list[str] | None = None,
) -> str:
    if concepts:
        listed = "\n".join(f"- {name}" for name in concepts)
        tagging = (
            "Set 'concept' on each item to the one entry from this list that the item "
            "tests, copied exactly. If none of them fit, set 'concept' to an empty "
            f"string.\nConcepts:\n{listed}\n"
        )
    else:
        tagging = "Set 'concept' to the short name of the idea each item tests.\n"

    working = (
        "" if quantitative else "Leave 'working' empty unless an item needs a calculation.\n"
    )
    repeats = ""
    if avoid:
        # A large set is written in batches; this keeps a later batch from
        # asking what an earlier one already did.
        listed_avoid = "\n".join(f"- {question[:160]}" for question in avoid)
        repeats = (
            "These questions are already in the set. Do not repeat them or test the "
            f"same point again:\n{listed_avoid}\n"
        )

    return (
        "You are setting revision material from the lecture content below.\n"
        f"{ITEM_INSTRUCTIONS[kind].format(count=count)}\n"
        f"{_QUALITY_RULES}"
        f"{_QUANTITATIVE_RULES if quantitative else ''}"
        f"{working}"
        f"Set 'kind' to '{kind.value}' on every item. Base every item strictly on "
        "the content provided - do not introduce outside material.\n"
        f"{tagging}{repeats}\n{source_text[:MAX_INPUT_CHARS]}"
    )


def grading_prompt(submissions: list[ShortAnswerSubmission]) -> str:
    # Reference on its own labelled line: wrapping it in brackets made the model
    # echo the brackets back as part of the reference, so every lookup missed.
    rendered = "\n\n".join(
        f"Reference: {submission.reference}\n"
        f"Question: {submission.question}\n"
        f"Model answer: {submission.expected_answer}\n"
        f"Student answer: {submission.student_answer}"
        for submission in submissions
    )
    return (
        "Mark each student answer below against its model answer. Award credit for "
        "an answer that conveys the same understanding, even if worded differently, "
        "less formally, or more briefly. Do not require the model answer's exact "
        "wording. Mark it incorrect if a key point is missing, contradicted, or the "
        "answer is blank, off-topic, or merely restates the question.\n"
        "Return exactly one grade per question, in the same order. Copy each "
        "'reference' exactly as given, with no added punctuation or brackets. Write "
        "'feedback' as one or two sentences addressed to the student, saying what was "
        "right or what was missing.\n\n"
        f"{rendered}"
    )


def same_concept_prompt(pairs: list[tuple[str, str]]) -> str:
    rendered = "\n\n".join(
        f"Pair {index}:\nA: {first}\nB: {second}"
        for index, (first, second) in enumerate(pairs, start=1)
    )
    return (
        "For each pair below, decide whether A and B describe the SAME academic "
        "concept, just worded differently, abbreviated, or pluralised.\n"
        "Answer true only if a lecturer would treat them as one entry in a glossary. "
        "Answer false when they are distinct but related ideas - different normal "
        "forms, different anomaly types, or a concept and a mechanism it uses - even "
        "when the wording is similar.\n"
        "Return one verdict per pair, in order, with 'pair' set to the pair number.\n\n"
        f"{rendered}"
    )


def course_summary_prompt(course_name: str, concepts: list[tuple[str, str]]) -> str:
    listed = "\n".join(f"- {name}: {summary}" for name, summary in concepts)
    return (
        "Below are the concepts extracted from a student's uploaded material for "
        f"the course {course_name}.\n"
        "Write a short overview, two or three sentences, of what the course covers "
        "so far. Address the student directly. Describe only what these concepts "
        "show - do not speculate about topics that are not listed, and do not "
        "mention that the list came from uploads.\n\n"
        f"{listed}"
    )


def timetable_prompt(known_courses: list[tuple[str, str]], extra_text: str = "") -> str:
    """Read a student's lecture timetable into structured weekly slots.

    The student confirms every row before anything is saved, so the model is
    told to leave out what it cannot read rather than guess at it - a missing
    row is easy to add by hand, a wrong time silently mistimes every reminder.
    """
    listed = "\n".join(f"- {code}: {name}" for code, name in known_courses) or "(none yet)"
    text_block = f"\n\nTimetable text:\n{extra_text[:MAX_INPUT_CHARS]}" if extra_text else ""
    return (
        "This is a university student's weekly lecture timetable. List every "
        "recurring class session in it.\n"
        "For each session give: 'title' (the course name or code as written), "
        "'course_code' (the course code if one is shown, otherwise an empty string), "
        "'day_of_week' (0 = Monday through 6 = Sunday), 'start_time' and 'end_time' "
        "in 24-hour HH:MM, and 'venue' (room or building, or an empty string).\n"
        "A course that meets on several days is several sessions. Skip anything "
        "whose day or time you cannot read with confidence rather than guessing.\n"
        "The student already has these courses; use the same code when a session "
        f"clearly matches one:\n{listed}"
        f"{text_block}"
    )


def course_list_prompt(extra_text: str = "") -> str:
    """Read a course list, registration slip or handbook page.

    The student picks which courses to keep afterwards, so the instruction is
    to list everything legible rather than to guess at what they study.
    """
    text_block = f"\n\nDocument text:\n{extra_text[:MAX_INPUT_CHARS]}" if extra_text else ""
    return (
        "This document lists university courses - a registration slip, programme "
        "handbook page, course outline or similar. List every course in it.\n"
        "For each give: 'code' (the course code exactly as written, e.g. 'MATH 223', "
        "or an empty string if none is shown), 'name' (the course title in title "
        "case), 'level' (the year level as 100, 200, 300 ... if the document says "
        "which year the course is in, otherwise 0) and 'semester' (1 or 2 if the "
        "document says, otherwise 0).\n"
        "List each course once. Skip headings, totals, credit counts and anything "
        "that is not a course."
        f"{text_block}"
    )


def transcription_prompt() -> str:
    return (
        "Transcribe this lecture material into plain text so it can be studied from. "
        "Keep every heading, definition, worked example, formula and step. Write all "
        "mathematics in LaTeX: $...$ inline and $$...$$ for displayed equations. "
        "Describe a graph or diagram in one sentence in square brackets. Do not add "
        "commentary, summaries or anything that is not in the material."
    )
