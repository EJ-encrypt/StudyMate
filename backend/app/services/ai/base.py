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
    # Which concept this item tests, so attempts can feed per-concept mastery.
    # Empty when the generator could not place it against a known concept.
    concept: str


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


class TimetableEntry(BaseModel):
    """One weekly lecture read from a timetable. No defaults, for Gemini's schema."""

    title: str
    course_code: str
    day_of_week: int
    start_time: str
    end_time: str
    venue: str


class AIProvider(ABC):
    """Swappable LLM backend for StudyMate's AI features."""

    @property
    @abstractmethod
    def embedding_model_id(self) -> str:
        """Identifies the model behind embed().

        Stored with every vector. Vectors from different models are not
        comparable - different geometry, often different dimensions - so
        similarity is only ever computed between vectors sharing this id.
        """

    @abstractmethod
    def extract_concepts(self, text: str, max_concepts: int = 10) -> list[ExtractedConcept]: ...

    @abstractmethod
    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
    ) -> list[GeneratedItem]: ...

    @abstractmethod
    def grade_short_answers(
        self,
        submissions: list[ShortAnswerSubmission],
    ) -> list[ShortAnswerGrade]:
        """Mark free-text answers in one call, so a submission costs one request."""

    @abstractmethod
    def summarise_course(self, course_name: str, concepts: list[tuple[str, str]]) -> str:
        """A short overview of what a course covers, from its concepts."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts for similarity comparison, in the order given."""

    @abstractmethod
    def are_same_concept(self, pairs: list[tuple[str, str]]) -> list[bool]:
        """Judge whether each pair names the same concept.

        Similarity alone cannot settle this: measured on real concept text,
        "Second Normal Form"/"Third Normal Form" scores *higher* than
        "TLB"/"Translation Lookaside Buffer", so the bands overlap. This
        adjudicates only the ambiguous middle.
        """

    def read_timetable(
        self,
        data: bytes,
        mime_type: str,
        known_courses: list[tuple[str, str]],
        extra_text: str = "",
    ) -> list[TimetableEntry]:
        """Read weekly lecture slots from a timetable image or PDF.

        Not abstract: an adapter without multimodal input can leave it out and
        the fallback chain simply moves on to one that has it.
        """
        raise NotImplementedError(f"{type(self).__name__} cannot read timetables")
