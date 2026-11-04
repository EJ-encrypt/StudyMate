import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConceptProgressRead(BaseModel):
    concept_id: uuid.UUID
    name: str
    summary: str
    # Null until the concept has been answered at least once: not practised
    # is a different state from practised badly.
    score: float | None
    attempts: int
    correct: int
    status: str
    last_seen_at: datetime | None
    # Filled for concepts in revision topics: where the student's material explains it.
    sources: list["ConceptSourceRead"] = []


class RevisionTopicRead(BaseModel):
    """Related concepts to revise together, named after the most central one."""

    title: str
    summary: str
    # The most urgent status among its concepts.
    status: str
    concepts: list[ConceptProgressRead]


class CoachSummary(BaseModel):
    course_id: uuid.UUID
    concept_count: int
    overall_mastery: float | None
    strong: int
    developing: int
    weak: int
    unpractised: int
    recommendations: list[ConceptProgressRead]
    # At most five, however many concepts need work.
    topics: list[RevisionTopicRead] = []
    # Concepts needing work beyond those grouped into topics.
    more_to_revise: int = 0
    concepts: list[ConceptProgressRead]


class ConceptSourceRead(BaseModel):
    """A document this concept was found in."""

    document_id: uuid.UUID
    filename: str
    # "Slide 4" or "Page 2" where the material marks it.
    location: str | None = None


class TopicExplainRequest(BaseModel):
    concept_ids: list[uuid.UUID] = Field(min_length=1, max_length=25)


class TopicExplanationRead(BaseModel):
    overview: str
    # Concept id -> how it ties into the topic, for the concepts that need work.
    links: dict[str, str]


class ConceptDetailRead(BaseModel):
    """Everything the Coach can say about one concept."""

    concept_id: uuid.UUID
    course_id: uuid.UUID
    name: str
    summary: str
    score: float | None
    attempts: int
    correct: int
    status: str
    last_seen_at: datetime | None
    # Where it came from, so a student can go back to the original material.
    sources: list[ConceptSourceRead]
    # What the lectures actually said about it, which may be phrased
    # differently in each one.
    mentions: list[str]


# ConceptProgressRead names ConceptSourceRead before it is defined.
ConceptProgressRead.model_rebuild()
