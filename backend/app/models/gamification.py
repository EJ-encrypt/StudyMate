import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentProgress(Base):
    """Running XP and streak for one student, across all their courses."""

    __tablename__ = "student_progress"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Date, not timestamp: a streak counts distinct days of study, and storing
    # the day directly is what the comparison actually needs.
    last_active_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class EarnedBadge(Base):
    """A badge a student has earned.

    Keyed to the student, not the course: the proposal's ERD linked Badge to
    Course many-to-many with no student junction, which cannot express "this
    student earned this badge" (PROJECT_PLAN.md flagged this to confirm).
    Badge definitions themselves live in code as a fixed catalogue, so there
    is no table of badge types to keep in step with it.
    """

    __tablename__ = "earned_badges"
    __table_args__ = (UniqueConstraint("student_id", "code", name="uq_earned_badge"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
