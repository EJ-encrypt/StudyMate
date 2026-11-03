"""Work out which lecture reminders are due, and send each exactly once.

Three per lecture: an hour before, when it starts, and when it ends (asking
the student to add notes or say what they learnt while it is fresh). The
scheduler ticks every minute, but a reminder stays due for a window of
several minutes so a delayed or skipped tick still sends it, and the
sent_reminders table makes sure it only goes out once.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.schedule import LectureSlot, SentReminder
from app.models.user import User
from app.services.notifications import Notification, notify

logger = logging.getLogger(__name__)

WINDOW = timedelta(minutes=10)
LEAD = timedelta(hours=1)

BEFORE = "before"
START = "start"
AFTER = "after"


@dataclass(frozen=True)
class DueReminder:
    slot: LectureSlot
    user: User
    kind: str
    occurs_on: date


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("Africa/Accra")


def _due_times(slot: LectureSlot, day: date, zone: ZoneInfo) -> dict[str, datetime]:
    start = datetime.combine(day, slot.start_time, zone)
    end = datetime.combine(day, slot.end_time, zone)
    if end <= start:
        # A slot typed as 23:00-01:00 ends the next day.
        end += timedelta(days=1)
    return {BEFORE: start - LEAD, START: start, AFTER: end}


def find_due(db: Session, now: datetime | None = None) -> list[DueReminder]:
    now = now or datetime.now(timezone.utc)
    due: list[DueReminder] = []

    rows = db.query(LectureSlot, User).join(User, LectureSlot.student_id == User.id).all()
    for slot, user in rows:
        if not (user.notify_push or user.notify_email):
            continue
        zone = _zone(user.timezone)
        local_today = now.astimezone(zone).date()
        # Yesterday covers an "after" for a lecture running past midnight;
        # tomorrow covers a "before" for a lecture just after midnight.
        for day in (local_today - timedelta(days=1), local_today, local_today + timedelta(days=1)):
            if day.weekday() != slot.day_of_week:
                continue
            for kind, at in _due_times(slot, day, zone).items():
                if at <= now < at + WINDOW:
                    due.append(DueReminder(slot=slot, user=user, kind=kind, occurs_on=day))
    return due


def _fmt(value: time) -> str:
    return value.strftime("%H:%M")


def compose(db: Session, reminder: DueReminder) -> Notification:
    slot = reminder.slot
    course = db.get(Course, slot.course_id) if slot.course_id else None
    name = f"{course.code} {slot.title}" if course and course.code not in slot.title else slot.title
    where = f" in {slot.venue}" if slot.venue else ""
    tag = f"lecture-{slot.id}-{reminder.occurs_on.isoformat()}"

    if reminder.kind == BEFORE:
        return Notification(
            title=f"{name} starts in 1 hour",
            body=f"{_fmt(slot.start_time)}-{_fmt(slot.end_time)}{where}. A quick look at last week's material now will make it easier to follow.",
            path="/schedule",
            tag=tag,
        )
    if reminder.kind == START:
        return Notification(
            title=f"{name} is starting now",
            body=f"Your lecture{where} is beginning. Note down anything that is new to you.",
            path="/schedule",
            tag=tag,
        )
    return Notification(
        title=f"How did {name} go?",
        body="Upload the slides or notes, or write a few lines on what you learnt while it is still fresh.",
        path=f"/lectures/{slot.id}/reflect",
        tag=tag,
    )


def send_due(db: Session, now: datetime | None = None) -> int:
    """Send every reminder that is due and not yet sent. Returns how many went out."""
    sent = 0
    due = find_due(db, now)
    if not due:
        return 0
    # Every tick inside the window sees the same reminders again; skip the
    # ones already sent without a failed insert for each.
    already = {
        (row.slot_id, row.occurs_on, row.kind)
        for row in db.query(SentReminder)
        .filter(SentReminder.slot_id.in_({reminder.slot.id for reminder in due}))
        .all()
    }
    for reminder in due:
        if (reminder.slot.id, reminder.occurs_on, reminder.kind) in already:
            continue
        # Claim first: the unique constraint means a second, overlapping tick
        # fails here instead of sending a duplicate.
        db.add(SentReminder(slot_id=reminder.slot.id, occurs_on=reminder.occurs_on, kind=reminder.kind))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue

        try:
            notify(db, reminder.user, compose(db, reminder))
            sent += 1
        except Exception:  # noqa: BLE001 -- one bad send must not stop the rest
            logger.exception("Reminder for slot %s failed", reminder.slot.id)
    return sent
