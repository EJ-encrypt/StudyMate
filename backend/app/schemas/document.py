import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class NotesCreate(BaseModel):
    course_id: uuid.UUID
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=200_000)


class UploadFileSpec(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=0)


class UploadRequest(BaseModel):
    course_id: uuid.UUID
    files: list[UploadFileSpec] = Field(min_length=1, max_length=20)


class UploadTargetRead(BaseModel):
    """Where and how the browser should send one file."""

    document_id: uuid.UUID
    filename: str
    original_filename: str
    method: str
    path: str
    token: str
    url: str


class CompletedUpload(BaseModel):
    document_id: uuid.UUID
    filename: str = Field(min_length=1, max_length=255)


class UploadComplete(BaseModel):
    course_id: uuid.UUID
    uploads: list[CompletedUpload] = Field(min_length=1, max_length=20)


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
