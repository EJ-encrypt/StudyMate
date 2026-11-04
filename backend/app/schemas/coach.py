import uuid
from datetime import datetime

from pydantic import BaseModel


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
