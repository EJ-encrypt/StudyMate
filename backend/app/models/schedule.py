import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LectureSlot(Base):
    """One recurring weekly lecture in a student's timetable."""

    __tablename__ = "lecture_slots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # Optional: a timetable can list a lecture before the student has made a
    # course for it. When set, the after-lecture prompt files notes there.
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # 0 = Monday ... 6 = Sunday, matching Python's date.weekday().
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    # Wall-clock times in the student's own time zone (users.timezone).
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    venue: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PushSubscription(Base):
    """A browser or phone that has agreed to receive push notifications."""

    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # The push service URL is unique per browser install, so it identifies the
    # device; re-subscribing the same browser updates rather than duplicates.
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SentReminder(Base):
    """Records that one reminder for one lecture on one day went out.

    The scheduler ticks every minute and a reminder is due for a window of
    several minutes, so without this a student would be notified repeatedly.
    The unique constraint makes sending idempotent even if two ticks overlap.
    """

    __tablename__ = "sent_reminders"
    __table_args__ = (
        UniqueConstraint("slot_id", "occurs_on", "kind", name="uq_sent_reminder"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lecture_slots.id", ondelete="CASCADE"), nullable=False
    )
    occurs_on: Mapped[date] = mapped_column(Date, nullable=False)
    # "before" (an hour ahead), "start", or "after" (prompt for notes).
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
