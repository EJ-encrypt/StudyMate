"""Chain several providers so one being rate-limited does not stop the app.

Each provider already retries and falls back between its own models. This adds
the outer layer: when a provider is exhausted, try the next one entirely.

Why this exists: measured against a live free-tier key, every Gemini Flash
model returned 503 or 429 simultaneously for minutes at a time. Within one
provider there was nowhere left to go. A second provider is the only thing
that helps, and it matters most during a usability session, where a
participant who cannot get past an upload has learned nothing about the
interface.
"""

import logging
from typing import Callable, TypeVar

from app.services.ai.base import (
    AIProvider,
    ExtractedConcept,
    GeneratedItem,
    ItemKind,
    ShortAnswerGrade,
    ShortAnswerSubmission,
    TimetableEntry,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackProvider(AIProvider):
    def __init__(self, providers: list[AIProvider]) -> None:
        if not providers:
            raise ValueError("FallbackProvider needs at least one provider")
        self._providers = providers

    @property
    def primary(self) -> AIProvider:
        return self._providers[0]

    @property
    def embedding_model_id(self) -> str:
        """Reports the primary's embedding model.

        Vectors are tagged with whichever provider actually produced them, so
        a fallback during embedding is recorded rather than silently mixed in
        with the primary's - comparing across models would be meaningless.
        """
        return self.primary.embedding_model_id

    def _first_that_works(self, operation: str, call: Callable[[AIProvider], T]) -> T:
        last_error: Exception | None = None

        for index, provider in enumerate(self._providers):
            try:
                return call(provider)
            except Exception as exc:  # noqa: BLE001 -- any failure moves to the next provider
                last_error = exc
                name = type(provider).__name__
                if index + 1 < len(self._providers):
                    logger.warning(
                        "%s failed %s (%s); trying %s",
                        name,
                        operation,
                        exc,
                        type(self._providers[index + 1]).__name__,
                    )
                else:
                    logger.warning("%s failed %s (%s); no providers left", name, operation, exc)

        assert last_error is not None
        raise last_error

    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]:
        return self._first_that_works(
            "extract_concepts", lambda p: p.extract_concepts(text, max_concepts)
        )

    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
    ) -> list[GeneratedItem]:
        return self._first_that_works(
            "generate_assessment_items",
            lambda p: p.generate_assessment_items(source_text, kind, count, concepts),
        )

    def grade_short_answers(
        self, submissions: list[ShortAnswerSubmission]
    ) -> list[ShortAnswerGrade]:
        return self._first_that_works(
            "grade_short_answers", lambda p: p.grade_short_answers(submissions)
        )

    def are_same_concept(self, pairs: list[tuple[str, str]]) -> list[bool]:
        return self._first_that_works("are_same_concept", lambda p: p.are_same_concept(pairs))

    def summarise_course(self, course_name: str, concepts: list[tuple[str, str]]) -> str:
        return self._first_that_works(
            "summarise_course", lambda p: p.summarise_course(course_name, concepts)
        )

    def read_timetable(
        self,
        data: bytes,
        mime_type: str,
        known_courses: list[tuple[str, str]],
        extra_text: str = "",
    ) -> list[TimetableEntry]:
        return self._first_that_works(
            "read_timetable",
            lambda p: p.read_timetable(data, mime_type, known_courses, extra_text),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Use embed_tagged: an embedding is only meaningful alongside the model "
            "that produced it."
        )

    def embed_tagged(self, texts: list[str]) -> tuple[list[list[float]], str]:
        """Embed, reporting which model succeeded.

        Unlike the other calls, the caller cannot treat the result as
        interchangeable: vectors from two different models are not comparable,
        so the identity has to travel with them.
        """
        last_error: Exception | None = None

        for index, provider in enumerate(self._providers):
            try:
                return provider.embed(texts), provider.embedding_model_id
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if index + 1 < len(self._providers):
                    logger.warning(
                        "%s failed embed (%s); trying %s",
                        type(provider).__name__,
                        exc,
                        type(self._providers[index + 1]).__name__,
                    )
                else:
                    logger.warning("%s failed embed (%s); no providers left", type(provider).__name__, exc)

        assert last_error is not None
        raise last_error
