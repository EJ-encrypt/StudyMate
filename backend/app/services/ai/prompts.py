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

MAX_INPUT_CHARS = 20000

ITEM_INSTRUCTIONS = {
    ItemKind.FLASHCARD: (
        "Write {count} flashcards. 'question' is the prompt side, 'answer' is the "
        "concise fact on the reverse. Leave 'options' empty."
    ),
    ItemKind.MCQ: (
        "Write {count} multiple-choice questions. 'question' is the stem, 'options' "
        "holds exactly four distinct answer choices, and 'answer' repeats the correct "
        "option verbatim. Wrong options must be plausible. Use 'explanation' to say "
        "briefly why the answer is right."
    ),
    ItemKind.SHORT_ANSWER: (
        "Write {count} short-answer questions. 'question' asks for an explanation a "
        "student can give in one to three sentences, 'answer' is the model answer "
        "marking should accept, and 'explanation' notes the key points that must "
        "appear for the answer to count. Leave 'options' empty."
    ),
    ItemKind.FILL_BLANK: (
        "Write {count} fill-in-the-blank questions. 'question' is a sentence with one "
        "missing term replaced by '_____', and 'answer' is only that term - one or two "
        "words, no punctuation. The blank must hide a meaningful piece of terminology "
        "the student should recall, never a symbol, operator or filler word, and enough "
        "of the sentence must remain for the answer to be unambiguous. Leave 'options' "
        "empty."
    ),
}


def concept_extraction_prompt(text: str, max_concepts: int) -> str:
    return (
        f"Extract up to {max_concepts} key academic concepts from this lecture "
        "material. For each concept give a short name and a one-sentence summary "
        f"of what it means.\n\n{text[:MAX_INPUT_CHARS]}"
    )


def generation_prompt(
    source_text: str,
    kind: ItemKind,
    count: int,
    concepts: list[str] | None = None,
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

    return (
        "You are setting revision material from the lecture content below.\n"
        f"{ITEM_INSTRUCTIONS[kind].format(count=count)}\n"
        f"Set 'kind' to '{kind.value}' on every item. Base every item strictly on "
        "the content provided - do not introduce outside material.\n"
        f"{tagging}\n{source_text[:MAX_INPUT_CHARS]}"
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
