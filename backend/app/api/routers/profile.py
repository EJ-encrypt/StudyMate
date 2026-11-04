from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assessment import Attempt
from app.models.social import GameRound
from app.models.user import User
from app.schemas.gamification import ProgressSummary
from app.services import review
from app.services.gamification import summary

router = APIRouter(prefix="/profile", tags=["profile"])

# Ten flashcards looked at counts as one study session towards the daily goal.
CARDS_PER_SESSION = 10


def start_of_today(user: User) -> datetime:
    """Midnight where the student is, as a UTC time."""
    try:
        zone = ZoneInfo(user.timezone or "Africa/Accra")
    except Exception:  # noqa: BLE001 -- an unknown zone falls back to UTC
        zone = ZoneInfo("UTC")
    local = datetime.now(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


def sessions_today(db: Session, user: User) -> int:
    """Arcade rounds and quizzes finished today, plus flashcards in tens."""
    since = start_of_today(user)
    rounds = (
        db.query(GameRound)
        .filter(GameRound.student_id == user.id, GameRound.submitted_at.isnot(None), GameRound.submitted_at >= since)
        .count()
    )
    quizzes = db.query(Attempt).filter(Attempt.student_id == user.id, Attempt.created_at >= since).count()
    cards = review.reviewed_since(db, user.id, since)
    return rounds + quizzes + cards // CARDS_PER_SESSION


@router.get("/progress", response_model=ProgressSummary)
def my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressSummary:
    db.commit()
    return ProgressSummary(
        **summary(db, current_user.id),
        daily_goal=current_user.daily_goal,
        done_today=sessions_today(db, current_user),
    )
