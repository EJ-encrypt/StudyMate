"""Spaced repetition for flashcards: when each card should come back."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FlashcardReview(Base):
    """A student's place in the Leitner boxes for one card (app/services/review.py)."""

    __tablename__ = "flashcard_reviews"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_items.id", ondelete="CASCADE"), primary_key=True
    )
    # 1 (still learning) to 5 (well known); higher boxes come back less often.
    box: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
