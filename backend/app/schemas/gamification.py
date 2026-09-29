from datetime import date, datetime

from pydantic import BaseModel


class BadgeRead(BaseModel):
    code: str
    name: str
    description: str
    # Null when the student has not earned it yet, so the profile can show
    # what is still available rather than only what is done.
    earned_at: datetime | None


class ProgressSummary(BaseModel):
    xp: int
    current_streak: int
    longest_streak: int
    last_active_on: date | None
    documents: int
    attempts: int
    badges: list[BadgeRead]
