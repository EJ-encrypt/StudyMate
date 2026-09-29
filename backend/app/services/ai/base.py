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
    SHORT_ANSWER = "short_answer"


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


class ShortAnswerSubmission(BaseModel):
    """One short answer awaiting marking, keyed so grades can be matched back."""

    reference: str
    question: str
    expected_answer: str
    student_answer: str


class ShortAnswerGrade(BaseModel):
    reference: str
    is_correct: bool
    feedback: str


class AIProvider(ABC):
    """Swappable LLM backend for StudyMate's AI features."""

    @abstractmethod
    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]: ...

    @abstractmethod
    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
    ) -> list[GeneratedItem]: ...

    @abstractmethod
    def grade_short_answers(
        self,
        submissions: list[ShortAnswerSubmission],
    ) -> list[ShortAnswerGrade]:
        """Mark free-text answers in one call, so a submission costs one request."""
