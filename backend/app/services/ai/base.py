from abc import ABC, abstractmethod

from pydantic import BaseModel


class ExtractedConcept(BaseModel):
    name: str
    summary: str


class AIProvider(ABC):
    """Swappable LLM backend for StudyMate's AI features.

    Only extract_concepts exists so far (Phase 1). generate_content and
    grade_short_answer join this interface in Phase 3, when assessment
    generation and grading are actually built (PROJECT_PLAN.md).
    """

    @abstractmethod
    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]: ...
