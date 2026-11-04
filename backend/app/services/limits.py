"""Daily limits on the AI work each student can ask for.

The AI providers are on free tiers with a shared daily quota. Without a cap,
one student uploading a hundred files, or a script hammering "generate",
would use it up and leave every other student with failing quizzes. The
window is a rolling 24 hours, so there is no midnight rush to reset.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.usage import AiUsage

WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class Limit:
    setting: str
    # Finishes "You have reached today's limit of N ...".
    noun: str


LIMITS = {
    "generate": Limit("limit_generate_per_day", "new question sets"),
    "document": Limit("limit_documents_per_day", "uploads to read"),
    "read": Limit("limit_reads_per_day", "photos of timetables or course lists"),
    "grade": Limit("limit_grading_per_day", "written answers marked by AI"),
}


def used(db: Session, student_id: uuid.UUID, kind: str) -> int:
    since = datetime.now(timezone.utc) - WINDOW
    total = (
        db.query(func.coalesce(func.sum(AiUsage.amount), 0))
        .filter(AiUsage.student_id == student_id, AiUsage.kind == kind, AiUsage.created_at >= since)
        .scalar()
    )
    return int(total or 0)


def allows(db: Session, student_id: uuid.UUID, kind: str, amount: int = 1) -> bool:
    return used(db, student_id, kind) + amount <= getattr(settings, LIMITS[kind].setting)


def check(db: Session, student_id: uuid.UUID, kind: str, amount: int = 1) -> None:
    """Refuse with 429 if `amount` more of `kind` would go over today's limit."""
    if amount > 0 and not allows(db, student_id, kind, amount):
        limit = LIMITS[kind]
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You have reached today's limit of {getattr(settings, limit.setting)} {limit.noun}. "
                "It frees up gradually over the next 24 hours."
            ),
        )


def spend(db: Session, student_id: uuid.UUID, kind: str, amount: int = 1) -> None:
    """Count `amount` of `kind` against the student's limit, or refuse with 429.

    Added to the session, not committed: the caller's commit records it with
    the work it pays for, so a request that fails part way costs nothing.
    """
    if amount <= 0:
        return
    check(db, student_id, kind, amount)
    db.add(AiUsage(student_id=student_id, kind=kind, amount=amount))
