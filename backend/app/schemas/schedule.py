import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.assessment import NewBadge


class SlotBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    course_id: uuid.UUID | None = None
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    venue: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def has_length(self) -> "SlotBase":
        if self.start_time == self.end_time:
            raise ValueError("A lecture must end after it starts")
        return self


class SlotCreate(SlotBase):
    pass


class SlotBulkCreate(BaseModel):
    slots: list[SlotCreate] = Field(min_length=1, max_length=60)
    # Replace the whole timetable, e.g. at the start of a new semester.
    replace: bool = False


class SlotUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    course_id: uuid.UUID | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    venue: str | None = Field(default=None, max_length=255)


class SlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    course_id: uuid.UUID | None
    course_code: str | None = None
    day_of_week: int
    start_time: time
    end_time: time
    venue: str


class SlotProposal(BaseModel):
    """A slot read from an uploaded timetable, not yet saved."""

    title: str
    course_id: uuid.UUID | None
    course_code: str
    day_of_week: int
    start_time: time
    end_time: time
    venue: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)
    p256dh: str = Field(min_length=10, max_length=255)
    auth: str = Field(min_length=4, max_length=255)


class PushSubscriptionDelete(BaseModel):
    endpoint: str


class NotificationConfig(BaseModel):
    vapid_public_key: str
    push_available: bool
    email_available: bool


class ReflectionCreate(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    # Needed only when the lecture is not linked to a course yet.
    course_id: uuid.UUID | None = None


class ReflectionResult(BaseModel):
    document_id: uuid.UUID
    course_id: uuid.UUID
    new_badges: list[NewBadge] = []
