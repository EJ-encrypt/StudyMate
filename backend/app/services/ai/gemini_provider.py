import logging
import random
import time

import requests
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.alignment import align_grades
from app.services.ai.base import (
    AIProvider,
    ExtractedConcept,
    GeneratedItem,
    ItemKind,
    ShortAnswerGrade,
    ShortAnswerSubmission,
)
from app.services.ai.prompts import (
    concept_extraction_prompt,
    generation_prompt,
    grading_prompt,
    course_summary_prompt,
    same_concept_prompt,
)

logger = logging.getLogger(__name__)

# Models come from GEMINI_MODELS, tried in order. Free-tier capacity is
# per-model and congestion shifts through the day -- measured against a live
# key, most Flash models returned 503 "high demand" while a lite variant
# answered fine, so a single model is not dependable. Google also retires
# models without notice (gemini-2.5-flash was closed to new keys mid-project),
# which is why the list is configuration rather than code.
# `client.models.list()` shows what a key can actually reach.

# 768 dimensions rather than the 3072 default: measured separation on concept
# text is the same, and the vectors are stored per concept.
_EMBEDDING_MODEL = "gemini-embedding-2"
_EMBEDDING_DIM = 768

# 5xx = busy or flaking, and worth another go a second later. 429 is different:
# it means the free-tier quota for that model is spent, which a two-second
# backoff cannot fix, so it is handled by _QUOTA_COOLDOWN below instead of by
# retrying. Without any retries one blip permanently fails a student's upload.
_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})
_QUOTA_EXHAUSTED_STATUS = 429
_ATTEMPTS_PER_MODEL = 2
_BACKOFF_BASE_SECONDS = 2.0

# How long to leave a quota-exhausted model alone. Measured: every call was
# paying two failed attempts plus a backoff on a model that had returned 429 all
# day (~9s of the ~13s each call took) before reaching one that answered.
# Short enough that a per-minute quota is picked up again promptly, long enough
# that a spent daily quota is only re-probed once a minute.
_QUOTA_COOLDOWN_SECONDS = 60.0
_quota_cooldown_until: dict[str, float] = {}


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


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._models = settings.gemini_models_list

    @property
    def embedding_model_id(self) -> str:
        return f"gemini:{_EMBEDDING_MODEL}:{_EMBEDDING_DIM}"

    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]:
        response = self._generate_with_retry(
            concept_extraction_prompt(text, max_concepts), _ConceptList
        )
        parsed = _ConceptList.model_validate_json(response.text)
        return parsed.concepts[:max_concepts]

    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
    ) -> list[GeneratedItem]:
        response = self._generate_with_retry(
            generation_prompt(source_text, kind, count, concepts), _ItemList
        )
        parsed = _ItemList.model_validate_json(response.text)
        return [item for item in parsed.items if item.kind == kind][:count]

    def grade_short_answers(
        self,
        submissions: list[ShortAnswerSubmission],
    ) -> list[ShortAnswerGrade]:
        if not submissions:
            return []

        response = self._generate_with_retry(grading_prompt(submissions), _GradeList)
        returned = _GradeList.model_validate_json(response.text).grades
        return align_grades(submissions, returned)

    def summarise_course(self, course_name: str, concepts: list[tuple[str, str]]) -> str:
        response = self._generate_with_retry(
            course_summary_prompt(course_name, concepts), _CourseSummary
        )
        return _CourseSummary.model_validate_json(response.text).summary.strip()

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

        response = self._generate_with_retry(same_concept_prompt(pairs), _VerdictList)
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


    def _generate_with_retry(self, prompt: str, schema: type[BaseModel]):
        """Retry transient failures, then fall back to the next model.

        Models whose quota is spent are skipped outright rather than retried:
        see _QUOTA_COOLDOWN_SECONDS.
        """
        last_error: Exception | None = None
        skipped: list[str] = []

        for model in self._models:
            if time.monotonic() < _quota_cooldown_until.get(model, 0.0):
                skipped.append(model)
                continue

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
                    if exc.code == _QUOTA_EXHAUSTED_STATUS:
                        # Out of quota, not busy. Waiting two seconds and asking
                        # the same model again only delays the fallback.
                        _quota_cooldown_until[model] = (
                            time.monotonic() + _QUOTA_COOLDOWN_SECONDS
                        )
                        last_error = exc
                        logger.warning(
                            "%s is out of quota; skipping it for %.0fs",
                            model,
                            _QUOTA_COOLDOWN_SECONDS,
                        )
                        break
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

        if last_error is None and skipped:
            # Everything is in cooldown, so nothing was actually tried. Clear the
            # cooldowns and let the next call probe again rather than reporting a
            # failure no request was ever made for.
            _quota_cooldown_until.clear()
            raise RuntimeError(
                "Every configured Gemini model is out of quota. "
                "Free-tier quota resets daily; try again later."
            )

        raise last_error
