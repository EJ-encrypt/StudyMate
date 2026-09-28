import enum
from abc import ABC, abstractmethod

from pydantic import BaseModel


class ExtractedConcept(BaseModel):
    name: str
    summary: str


class ItemKind(str, enum.Enum):
    FLASHCARD = "flashcard"
    MCQ = "mcq"
    FILL_BLANK = "fill_blank"


class GeneratedItem(BaseModel):
    """One generated revision item.

    Every field is required with no default: Gemini rejects a response
    schema that carries defaults ("Default value is not supported in the
    response schema"). Kinds without choices return an empty options list.
    """

    kind: ItemKind
    question: str
    answer: str
    options: list[str]
    explanation: str


class AIProvider(ABC):
    """Swappable LLM backend for StudyMate's AI features.

    grade_short_answer joins this interface alongside short-answer and
    exam generation, once that grading approach is settled
    (PROJECT_PLAN.md open items).
    """

    @abstractmethod
    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]: ...

    @abstractmethod
    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
    ) -> list[GeneratedItem]: ...
