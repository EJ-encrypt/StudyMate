import re
import uuid
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


_USERNAME = re.compile(r"^[a-z0-9_.]{3,30}$")


def _valid_timezone(value: str | None) -> str | None:
    if value is not None and value not in available_timezones():
        raise ValueError(f"Unknown time zone {value!r}")
    return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    username: str | None = None
    role: UserRole
    school: str | None = None
    programme: str | None = None
    level: int | None = None
    semester: int | None = None
    timezone: str = "Africa/Accra"
    notify_push: bool = True
    notify_email: bool = True
    tutorial_seen: bool = False
    public_leaderboard: bool = False

    @property
    def needs_onboarding(self) -> bool:
        return self.school is None


class OnboardingUpdate(BaseModel):
    """Captured once, right after registering."""

    school: str = Field(min_length=1, max_length=150)
    programme: str = Field(min_length=1, max_length=150)
    level: int = Field(ge=100, le=900)
    semester: int = Field(ge=1, le=2)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    # Sent by the browser, so reminders fire in the student's own local time.
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        return _valid_timezone(value)


class PreferencesUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    # An empty string clears it.
    username: str | None = None
    level: int | None = Field(default=None, ge=100, le=900)
    semester: int | None = Field(default=None, ge=1, le=2)
    timezone: str | None = None
    notify_push: bool | None = None
    notify_email: bool | None = None
    tutorial_seen: bool | None = None
    public_leaderboard: bool | None = None
    programme: str | None = Field(default=None, min_length=1, max_length=150)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lstrip("@").lower()
        if value and not _USERNAME.match(value):
            raise ValueError("Use 3 to 30 letters, numbers, dots or underscores")
        return value

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        return _valid_timezone(value)
