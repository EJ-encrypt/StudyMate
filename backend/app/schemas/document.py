import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class NotesCreate(BaseModel):
    course_id: uuid.UUID
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=200_000)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    filename: str
    status: DocumentStatus
    error_message: str | None
    can_retry: bool
    created_at: datetime


class ConceptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    summary: str


class DocumentDetail(DocumentRead):
    concepts: list[ConceptRead] = []
