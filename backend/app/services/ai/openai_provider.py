"""OpenAI adapter.

UNVERIFIED AGAINST THE LIVE API. Written from the published SDK shape
(`client.responses.parse(model=..., input=..., text_format=...)` returning
`.output_parsed`) but never executed against a real key, because none was
available. The Gemini adapter needed three fixes that only appeared against
the real service - a retired model id, a schema that rejected default values,
and a prompt that made the model echo brackets into identifiers - so expect
something here to need correcting on first contact. Model names come from
configuration (`OPENAI_MODELS`) precisely so a wrong one is fixable without
touching code.
"""

import base64
import logging
import random
import time

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.base import (
    AIProvider,
    ExtractedConcept,
    GeneratedItem,
    ItemKind,
    ShortAnswerGrade,
    ShortAnswerSubmission,
    TimetableEntry,
)
from app.services.ai.alignment import align_grades
from app.services.ai.prompts import (
    concept_extraction_prompt,
    generation_prompt,
    grading_prompt,
    course_summary_prompt,
    same_concept_prompt,
    timetable_prompt,
)

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "text-embedding-3-small"
_MAX_INPUT_CHARS = 20000
_ATTEMPTS_PER_MODEL = 2
_BACKOFF_BASE_SECONDS = 2.0
_RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})


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


class _CourseSummary(BaseModel):
    summary: str


class _Timetable(BaseModel):
    entries: list[TimetableEntry]


class OpenAIProvider(AIProvider):
    def __init__(self) -> None:
        # The SDK's own default is a 10-minute timeout with two silent retries,
        # far beyond Vercel's 5-minute limit; retries are handled below instead.
        self._client = OpenAI(api_key=settings.openai_api_key, timeout=60.0, max_retries=0)
        self._models = settings.openai_models_list

    @property
    def embedding_model_id(self) -> str:
        return f"openai:{_EMBEDDING_MODEL}"

    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]:
        parsed = self._parse(
            concept_extraction_prompt(text[:_MAX_INPUT_CHARS], max_concepts), _ConceptList
        )
        return parsed.concepts[:max_concepts]

    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
    ) -> list[GeneratedItem]:
        parsed = self._parse(
            generation_prompt(source_text[:_MAX_INPUT_CHARS], kind, count, concepts), _ItemList
        )
        return [item for item in parsed.items if item.kind == kind][:count]

    def grade_short_answers(
        self, submissions: list[ShortAnswerSubmission]
    ) -> list[ShortAnswerGrade]:
        if not submissions:
            return []
        parsed = self._parse(grading_prompt(submissions), _GradeList)
        return align_grades(submissions, parsed.grades)

    def summarise_course(self, course_name: str, concepts: list[tuple[str, str]]) -> str:
        parsed = self._parse(course_summary_prompt(course_name, concepts), _CourseSummary)
        return parsed.summary.strip()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = self._client.embeddings.create(model=_EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in result.data]

    def are_same_concept(self, pairs: list[tuple[str, str]]) -> list[bool]:
        if not pairs:
            return []
        parsed = self._parse(same_concept_prompt(pairs), _VerdictList)
        by_number = {verdict.pair: verdict.same for verdict in parsed.verdicts}
        return [by_number.get(index, False) for index in range(1, len(pairs) + 1)]

    def read_timetable(
        self,
        data: bytes,
        mime_type: str,
        known_courses: list[tuple[str, str]],
        extra_text: str = "",
    ) -> list[TimetableEntry]:
        content: list[dict] = [{"type": "input_text", "text": timetable_prompt(known_courses, extra_text)}]
        if data:
            encoded = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
            if mime_type.startswith("image/"):
                content.insert(0, {"type": "input_image", "image_url": encoded})
            else:
                content.insert(0, {"type": "input_file", "filename": "timetable.pdf", "file_data": encoded})
        return self._parse(content, _Timetable).entries

    def _parse(self, prompt: str | list[dict], schema: type[BaseModel]):
        """Structured request with retry, then fall back to the next model."""
        last_error: Exception | None = None

        for model in self._models:
            for attempt in range(1, _ATTEMPTS_PER_MODEL + 1):
                try:
                    response = self._client.responses.parse(
                        model=model,
                        input=[{"role": "user", "content": prompt}],
                        text_format=schema,
                    )
                    parsed = response.output_parsed
                    if parsed is None:
                        raise ValueError("OpenAI returned no parsed output")
                    return parsed
                except (RateLimitError, APIConnectionError) as exc:
                    last_error = exc
                    reason = type(exc).__name__
                except APIStatusError as exc:
                    if exc.status_code not in _RETRYABLE_STATUS:
                        raise
                    last_error = exc
                    reason = f"HTTP {exc.status_code}"

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

        raise last_error if last_error else RuntimeError("No OpenAI model configured")
