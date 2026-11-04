"""Friends, leaderboards and challenges.

Privacy rules, deliberately simple:
- Friends see each other's name, username and XP.
- The programme leaderboard is opt-in and shows usernames (or "Ama M." when
  there is none), never email addresses.
- Someone can only be found by their exact username, so the app cannot be
  used to browse who else is on it.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.gamification import StudentProgress
from app.models.social import Challenge, Friendship, XpEvent
from app.models.user import User

CHALLENGE_HOURS = 48
CHALLENGE_WIN_XP = 20
CHALLENGE_DRAW_XP = 10
LEADERBOARD_SIZE = 50

# Degree prefixes and filler that vary between how students write the same
# programme. "BSc. Information Technology", "BSc IT", "Bachelor of Science in
# Information Technology" and "Information Technology" all end up as
# "information technology".
_DEGREE_PHRASE = re.compile(r"\bbachelor'?s? of (science|arts|education|engineering|commerce|laws)\b")
_DEGREE = re.compile(r"\b(b ?sc|b ?a|bba|b ?ed|b ?eng|b ?com|llb|mb ?chb|bachelors?|hons|honours|degree)\b")
_FILLER = {"of", "in", "the"}
_ABBREVIATIONS = {
    "it": "information technology",
    "cs": "computer science",
    "ict": "information and communication technology",
    "econs": "economics",
    "maths": "mathematics",
    "math": "mathematics",
    "stats": "statistics",
    "admin": "administration",
}


def programme_key(programme: str | None) -> str:
    """A comparison form of a programme name, so spellings of one programme group together."""
    if not programme:
        return ""
    text = programme.lower().replace("&", " and ")
    text = re.sub(r"[^a-z' ]", " ", text.replace(".", ""))
    text = _DEGREE.sub(" ", _DEGREE_PHRASE.sub(" ", text))
    words = [_ABBREVIATIONS.get(word, word) for word in text.split() if word not in _FILLER]
    return " ".join(" ".join(words).split())


def public_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    parts = user.full_name.split()
    return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else (parts[0] if parts else "Student")


# --- Friends ----------------------------------------------------------------


def _between(a: uuid.UUID, b: uuid.UUID):
    return or_(
        (Friendship.requester_id == a) & (Friendship.addressee_id == b),
        (Friendship.requester_id == b) & (Friendship.addressee_id == a),
    )


def friendship(db: Session, a: uuid.UUID, b: uuid.UUID) -> Friendship | None:
    return db.query(Friendship).filter(_between(a, b)).first()


def friend_ids(db: Session, student_id: uuid.UUID) -> list[uuid.UUID]:
    rows = db.query(Friendship).filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == student_id, Friendship.addressee_id == student_id),
    )
    return [row.addressee_id if row.requester_id == student_id else row.requester_id for row in rows]


def are_friends(db: Session, a: uuid.UUID, b: uuid.UUID) -> bool:
    row = friendship(db, a, b)
    return row is not None and row.status == "accepted"


# --- Leaderboards -------------------------------------------------------------


def week_start(now: datetime | None = None) -> datetime:
    """Monday 00:00 UTC, which is also midnight in Ghana."""
    now = now or datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).date()
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


@dataclass
class Standing:
    rank: int
    student_id: uuid.UUID
    name: str
    username: str | None
    programme: str | None
    xp: int
    is_me: bool


def _xp(db: Session, student_ids: list[uuid.UUID], period: str) -> dict[uuid.UUID, int]:
    if not student_ids:
        return {}
    if period == "week":
        rows = (
            db.query(XpEvent.student_id, func.coalesce(func.sum(XpEvent.amount), 0))
            .filter(XpEvent.student_id.in_(student_ids), XpEvent.created_at >= week_start())
            .group_by(XpEvent.student_id)
        )
    else:
        rows = db.query(StudentProgress.student_id, StudentProgress.xp).filter(
            StudentProgress.student_id.in_(student_ids)
        )
    return {student_id: int(xp) for student_id, xp in rows}


def leaderboard(db: Session, me: User, scope: str, period: str) -> list[Standing]:
    """Ranked XP. Friends always include the student; the programme board only opted-in students."""
    if scope == "friends":
        users = db.query(User).filter(User.id.in_([me.id, *friend_ids(db, me.id)])).all()
        show_real_names = True
    else:
        key = programme_key(me.programme)
        if not key:
            return []
        users = [
            user
            for user in db.query(User).filter(User.public_leaderboard.is_(True)).all()
            if programme_key(user.programme) == key
        ]
        show_real_names = False

    xp = _xp(db, [user.id for user in users], period)
    ordered = sorted(users, key=lambda user: (-xp.get(user.id, 0), user.full_name.lower()))
    standings = [
        Standing(
            rank=index + 1,
            student_id=user.id,
            name=user.full_name if show_real_names else public_name(user),
            username=user.username,
            programme=user.programme,
            xp=xp.get(user.id, 0),
            is_me=user.id == me.id,
        )
        for index, user in enumerate(ordered)
    ]
    top = standings[:LEADERBOARD_SIZE]
    # Always show where the student stands, even below the cut.
    mine = next((s for s in standings if s.is_me), None)
    if mine and mine not in top:
        top.append(mine)
    return top


# --- Challenges ---------------------------------------------------------------


def expire_old(db: Session, student_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    db.query(Challenge).filter(
        Challenge.status == "open",
        Challenge.expires_at < now,
        or_(Challenge.challenger_id == student_id, Challenge.opponent_id == student_id),
    ).update({Challenge.status: "expired"}, synchronize_session=False)


def new_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=CHALLENGE_HOURS)
