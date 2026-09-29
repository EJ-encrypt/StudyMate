import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment import AssessmentKind, AssessmentStatus, ItemKind


class AssessmentCreate(BaseModel):
    document_id: uuid.UUID
    kind: AssessmentKind
    count: int = Field(default=10, ge=1, le=20)


class AssessmentItemRead(BaseModel):
    """The student-facing view of an item.

    Flashcards are self-reviewed, so they carry their answer. Graded kinds
    leave it null until an attempt is submitted, so the page cannot hand
    the student the answer key.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    kind: ItemKind
    question: str
    options: list[str]
    answer: str | None = None
    explanation: str | None = None


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    kind: AssessmentKind
    status: AssessmentStatus
    error_message: str | None
    created_at: datetime


class AssessmentDetail(AssessmentRead):
    items: list[AssessmentItemRead] = []


class AnswerSubmission(BaseModel):
    item_id: uuid.UUID
    response: str


class AttemptCreate(BaseModel):
    answers: list[AnswerSubmission]


class GradedAnswer(BaseModel):
    item_id: uuid.UUID
    response: str
    is_correct: bool
    correct_answer: str
    explanation: str


class AttemptResult(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    correct_count: int
    total_count: int
    answers: list[GradedAnswer]
