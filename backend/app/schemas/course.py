import uuid

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    # Default to the student's current level/semester when omitted.
    level: int | None = Field(default=None, ge=100, le=900)
    semester: int | None = Field(default=None, ge=1, le=2)


class CourseBulkCreate(BaseModel):
    """The courses a student ticked after importing a course list."""

    courses: list[CourseCreate] = Field(min_length=1, max_length=40)


class CourseProposal(BaseModel):
    """One course read from an uploaded list, for the student to confirm."""

    code: str
    name: str
    # None when the document did not say.
    level: int | None
    semester: int | None
    # Already in My Courses, so the page can show it as added rather than
    # offering to create a duplicate.
    already_added: bool


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
