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


class CoachSummary(BaseModel):
    course_id: uuid.UUID
    concept_count: int
    overall_mastery: float | None
    strong: int
    developing: int
    weak: int
    unpractised: int
    recommendations: list[ConceptProgressRead]
    concepts: list[ConceptProgressRead]
