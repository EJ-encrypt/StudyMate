import logging
import random
import time

import requests
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.base import (
    AIProvider,
    ExtractedConcept,
    GeneratedItem,
    ItemKind,
    ShortAnswerGrade,
    ShortAnswerSubmission,
)

logger = logging.getLogger(__name__)

# Free-tier Flash model on Google AI Studio (no billing required). Google
# retires these periodically -- gemini-2.5-flash was closed to new keys and the
# API itself pointed here. `client.models.list()` shows what a key can reach.
# Tried in order. Free-tier capacity is per-model and congestion shifts
# through the day -- measured against a live key, most Flash models returned
# 503 "high demand" while a lite variant answered fine, so a single model is
# not dependable here. `client.models.list()` shows what a key can reach.
_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
_MAX_INPUT_CHARS = 20000

# 768 dimensions rather than the 3072 default: measured separation on concept
# text is the same, and the vectors are stored per concept.
_EMBEDDING_MODEL = "gemini-embedding-2"
_EMBEDDING_DIM = 768

# 429 = free-tier quota, 5xx = busy or flaking. All transient: without retries
# one blip permanently fails a student's upload.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_ATTEMPTS_PER_MODEL = 2
_BACKOFF_BASE_SECONDS = 2.0


class _ConceptList(BaseModel):
    concepts: list[ExtractedConcept]


class _ItemList(BaseModel):
    items: list[GeneratedItem]


class _GradeList(BaseModel):
    grades: list[ShortAnswerGrade]


class _ConceptVerdict(BaseModel):
    pair: int
    same: bool


class _VerdictList(BaseModel):
    verdicts: list[_ConceptVerdict]


def _clean_reference(reference: str) -> str:
    return reference.strip().strip("[]()\"'").strip().lower()


_ITEM_INSTRUCTIONS = {
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


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]:
        truncated = text[:_MAX_INPUT_CHARS]
        prompt = (
            f"Extract up to {max_concepts} key academic concepts from this lecture "
            "material. For each concept give a short name and a one-sentence summary "
            f"of what it means.\n\n{truncated}"
        )
        response = self._generate_with_retry(prompt, _ConceptList)
        parsed = _ConceptList.model_validate_json(response.text)
        return parsed.concepts[:max_concepts]

    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
    ) -> list[GeneratedItem]:
        truncated = source_text[:_MAX_INPUT_CHARS]

        if concepts:
            listed = "\n".join(f"- {name}" for name in concepts)
            tagging = (
                "Set 'concept' on each item to the one entry from this list that the item "
                "tests, copied exactly. If none of them fit, set 'concept' to an empty "
                f"string.\nConcepts:\n{listed}\n"
            )
        else:
            tagging = "Set 'concept' to the short name of the idea each item tests.\n"

        prompt = (
            f"You are setting revision material from the lecture content below.\n"
            f"{_ITEM_INSTRUCTIONS[kind].format(count=count)}\n"
            f"Set 'kind' to '{kind.value}' on every item. Base every item strictly on "
            f"the content provided - do not introduce outside material.\n"
            f"{tagging}\n{truncated}"
        )
        response = self._generate_with_retry(prompt, _ItemList)
        parsed = _ItemList.model_validate_json(response.text)
        return [item for item in parsed.items if item.kind == kind][:count]

    def grade_short_answers(
        self,
        submissions: list[ShortAnswerSubmission],
    ) -> list[ShortAnswerGrade]:
        if not submissions:
            return []

        # Reference on its own labelled line: wrapping it in brackets made the
        # model echo the brackets back as part of the reference.
        rendered = "\n\n".join(
            f"Reference: {submission.reference}\n"
            f"Question: {submission.question}\n"
            f"Model answer: {submission.expected_answer}\n"
            f"Student answer: {submission.student_answer}"
            for submission in submissions
        )
        prompt = (
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

        response = self._generate_with_retry(prompt, _GradeList)
        returned = _GradeList.model_validate_json(response.text).grades
        return self._align_grades(submissions, returned)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = self._client.models.embed_content(
            model=_EMBEDDING_MODEL,
            contents=texts,
            config={"output_dimensionality": _EMBEDDING_DIM},
        )
        return [embedding.values for embedding in result.embeddings]

    def are_same_concept(self, pairs: list[tuple[str, str]]) -> list[bool]:
        if not pairs:
            return []

        rendered = "\n\n".join(
            f"Pair {index}:\nA: {first}\nB: {second}"
            for index, (first, second) in enumerate(pairs, start=1)
        )
        prompt = (
            "For each pair below, decide whether A and B describe the SAME academic "
            "concept, just worded differently, abbreviated, or pluralised.\n"
            "Answer true only if a lecturer would treat them as one entry in a glossary. "
            "Answer false when they are distinct but related ideas - different normal "
            "forms, different anomaly types, or a concept and a mechanism it uses - even "
            "when the wording is similar.\n"
            "Return one verdict per pair, in order, with 'pair' set to the pair number.\n\n"
            f"{rendered}"
        )

        response = self._generate_with_retry(prompt, _VerdictList)
        verdicts = _VerdictList.model_validate_json(response.text).verdicts
        by_number = {verdict.pair: verdict.same for verdict in verdicts}

        # An unanswered pair stays unmerged: a missed merge leaves a duplicate,
        # while a wrong merge silently loses a concept from the knowledge base.
        results = []
        for index in range(1, len(pairs) + 1):
            if index not in by_number:
                logger.warning("No verdict for concept pair %s; leaving unmerged", index)
            results.append(by_number.get(index, False))
        return results

    @staticmethod
    def _align_grades(
        submissions: list[ShortAnswerSubmission],
        returned: list[ShortAnswerGrade],
    ) -> list[ShortAnswerGrade]:
        """Match grades to submissions, tolerating how the model echoes references.

        Models decorate the reference (brackets, quotes, stray whitespace), so
        matching is done on a cleaned form. If a reference still cannot be
        matched but the counts line up, order is trusted instead. Anything left
        over is reported unmarked rather than risking a grade being attributed
        to the wrong question.
        """
        by_reference = {_clean_reference(grade.reference): grade for grade in returned}
        positional = returned if len(returned) == len(submissions) else []

        results = []
        for index, submission in enumerate(submissions):
            grade = by_reference.get(_clean_reference(submission.reference))
            if grade is None and positional:
                grade = positional[index]
                logger.warning(
                    "Reference %s not echoed back; matched grade by position",
                    submission.reference,
                )

            if grade is None:
                logger.warning("No grade returned for %s; marking as needing review", submission.reference)
                results.append(
                    ShortAnswerGrade(
                        reference=submission.reference,
                        is_correct=False,
                        feedback=(
                            "Automatic marking is unavailable for this answer. "
                            "Compare it with the model answer."
                        ),
                    )
                )
            else:
                # Return our own reference so callers can always match on it.
                results.append(
                    ShortAnswerGrade(
                        reference=submission.reference,
                        is_correct=grade.is_correct,
                        feedback=grade.feedback,
                    )
                )
        return results

    def _generate_with_retry(self, prompt: str, schema: type[BaseModel]):
        """Retry transient failures, then fall back to the next model."""
        last_error: Exception | None = None

        for model in _MODELS:
            for attempt in range(1, _ATTEMPTS_PER_MODEL + 1):
                try:
                    return self._client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=schema,
                        ),
                    )
                except errors.APIError as exc:
                    if exc.code not in _RETRYABLE_STATUS:
                        raise
                    last_error = exc
                    reason = f"HTTP {exc.code}"
                except requests.exceptions.RequestException as exc:
                    last_error = exc
                    reason = type(exc).__name__

                if attempt < _ATTEMPTS_PER_MODEL:
                    delay = _BACKOFF_BASE_SECONDS * 2 ** (attempt - 1) + random.uniform(0, 1)
                    logger.warning(
                        "%s unavailable (%s), attempt %s/%s; retrying in %.1fs",
                        model,
                        reason,
                        attempt,
                        _ATTEMPTS_PER_MODEL,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning("%s unavailable (%s); falling back", model, reason)

        raise last_error
