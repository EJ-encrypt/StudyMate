import uuid

from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    name: str
    code: str


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    owner_id: uuid.UUID
