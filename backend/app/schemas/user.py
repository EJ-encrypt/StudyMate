import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.STUDENT

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    school: str | None = None
    programme: str | None = None
    level: int | None = None
    semester: int | None = None

    @property
    def needs_onboarding(self) -> bool:
        return self.school is None


class OnboardingUpdate(BaseModel):
    """Captured once, right after registering."""

    school: str = Field(min_length=1, max_length=150)
    programme: str = Field(min_length=1, max_length=150)
    level: int = Field(ge=100, le=900)
    semester: int = Field(ge=1, le=2)
