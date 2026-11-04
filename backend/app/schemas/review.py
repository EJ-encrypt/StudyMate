import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.assessment import AssessmentItemRead


class ReviewCreate(BaseModel):
    remembered: bool


class ReviewRead(BaseModel):
    item_id: uuid.UUID
    box: int
    due_at: datetime


class DueCards(BaseModel):
    items: list[AssessmentItemRead]


class CourseDueRead(BaseModel):
    course_id: uuid.UUID
    code: str
    name: str
    due: int
