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


class ItemDraft(BaseModel):
    """What the model is asked to return for one item.

    The same as GeneratedItem plus 'working', placed before 'answer'. Models
    fill fields in schema order, so this makes them work a calculation out
    before committing to its result instead of guessing the number first -
    which is what made computed answers on maths material unreliable.
    """

    kind: ItemKind
    question: str
    working: str
    answer: str
    options: list[str]
    explanation: str
    concept: str

    def to_item(self) -> GeneratedItem:
        from app.services.latex import repair

        return GeneratedItem(
            kind=self.kind,
            question=repair(self.question),
            answer=repair(self.answer),
            options=[repair(option) for option in self.options],
            explanation=repair(self.explanation),
            concept=self.concept,
        )


class CourseEntry(BaseModel):
    """One course read from a course list or registration slip. No defaults, for Gemini."""

    code: str
    name: str
    # 0 when the document does not say.
    level: int
    semester: int


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


class ConceptLink(BaseModel):
    """How one concept ties into the topic it is grouped under."""

    name: str
    link: str


class TopicExplanation(BaseModel):
    """What ties a group of concepts together, for revising them as one topic."""

    overview: str
    links: list[ConceptLink]


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
    def extract_concepts(
        self, text: str, max_concepts: int = 10, quantitative: bool = False
    ) -> list[ExtractedConcept]: ...

    @abstractmethod
    def generate_assessment_items(
        self,
        source_text: str,
        kind: ItemKind,
        count: int = 10,
        concepts: list[str] | None = None,
        quantitative: bool = False,
        avoid: list[str] | None = None,
    ) -> list[GeneratedItem]:
        """Write one batch of items.

        `quantitative` switches on the maths rules (LaTeX, worked problems,
        mistake-based distractors); `avoid` lists questions an earlier batch of
        the same set already asked.
        """

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

    def explain_topic(self, course_name: str, concepts: list[tuple[str, str, bool]]) -> TopicExplanation:
        """How a group of related concepts fit together; (name, summary, needs work) each."""
        raise NotImplementedError(f"{type(self).__name__} cannot explain topics")

    def read_course_list(self, data: bytes, mime_type: str, extra_text: str = "") -> list[CourseEntry]:
        """Read the courses on a course list, registration slip or handbook page."""
        raise NotImplementedError(f"{type(self).__name__} cannot read course lists")

    def transcribe_document(self, data: bytes, mime_type: str) -> str:
        """Read a PDF or image into text, writing mathematics as LaTeX.

        Used where plain text extraction loses what matters: equations in a
        maths PDF come out of pdfplumber as scrambled symbols, and a photo of
        notes has no text layer at all.
        """
        raise NotImplementedError(f"{type(self).__name__} cannot transcribe documents")
