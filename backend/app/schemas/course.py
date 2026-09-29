import uuid

from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    name: str
    code: str
    # Default to the student's current level/semester when omitted.
    level: int | None = None
    semester: int | None = None


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    owner_id: uuid.UUID
    level: int
    semester: int
    summary: str | None = None
    document_count: int = 0


class CourseConceptRead(BaseModel):
    """One entry in the cumulative knowledge base."""

    id: uuid.UUID
    name: str
    summary: str
    document_count: int
