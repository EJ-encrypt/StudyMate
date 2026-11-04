"""Friends, challenges, stored game rounds and the XP log behind leaderboards."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Friendship(Base):
    """A friend request, and once accepted, the friendship itself.

    One row per pair, whoever asked first. Accepted friendships are symmetric:
    queries look at both columns.
    """

    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    addressee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # "pending" or "accepted". A declined request is deleted, so it can be sent again later.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GameRound(Base):
    """A dealt Arcade round, kept so the score is marked against what was dealt.

    Also what a challenge sends to a friend: they play this exact round, from
    the payload, even though the material behind it is not theirs.
    """

    __tablename__ = "game_rounds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    game: Mapped[str] = mapped_column(String(30), nullable=False)
    # The round as dealt, answers included.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Set when the dealer submits it, so one round cannot be scored twice.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Challenge(Base):
    """A friend is asked to beat the challenger's score on the same round."""

    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("game_rounds.id"), nullable=False)
    challenger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    opponent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    game: Mapped[str] = mapped_column(String(30), nullable=False)
    # Shown to the opponent, who does not have the course: "MATH 223 · Calculus II".
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    challenger_score: Mapped[int] = mapped_column(Integer, nullable=False)
    opponent_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "open", "completed" or "expired".
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class XpEvent(Base):
    """Every XP award, so leaderboards can count this week as well as all time."""

    __tablename__ = "xp_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # What earned it: "quiz", "game", "upload", "challenge".
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class UserBlock(Base):
    """One student has blocked another: no friend requests or challenges either way."""

    __tablename__ = "user_blocks"

    blocker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    blocked_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserReport(Base):
    """A report about another student, read from the Supabase table editor."""

    __tablename__ = "user_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    reported_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # "username", "spam", "harassment" or "other".
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    # "open" until someone has looked at it.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
