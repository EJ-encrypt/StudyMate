import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    LECTURER = "lecturer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # Legacy: passwords now live in Supabase Auth. Kept nullable so accounts
    # created before the move are not lost by a destructive migration.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional handle chosen in Settings. Stored lowercase; unique.
    username: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    # values_callable keeps the lowercase member *values* in Postgres; without it
    # SQLAlchemy would persist member names ("STUDENT") and break the enum type.
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        default=UserRole.STUDENT,
        nullable=False,
    )
    # Academic profile, captured once at onboarding. Null until then, which is
    # how the app knows to show the onboarding step.
    school: Mapped[str | None] = mapped_column(String(150), nullable=True)
    programme: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Current level (100, 200, ...) and semester (1 or 2). Courses carry their
    # own copies so earlier levels stay browsable after the student moves on.
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # IANA zone the lecture timetable is written in, e.g. "Africa/Accra".
    # Reminders are computed in it so "9:00" means nine o'clock where the
    # student is, not on the server.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Accra")
    notify_push: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Whether the first-run walkthrough has been finished or skipped. Kept on
    # the account rather than in the browser, so dismissing it on a laptop
    # also dismisses it on a phone.
    tutorial_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Opt-in: appear on the leaderboard for everyone on the same programme,
    # under the username. Friends always see each other regardless.
    public_leaderboard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # How many study sessions (Arcade rounds, quizzes, flashcard reviews) make a
    # good day, shown as a ring on Profile. Chosen in Settings.
    daily_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")
