import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConceptMastery(Base):
    """How well one student knows one concept, updated as they answer questions.

    Kept as a running figure rather than recomputed from every past answer so
    the Coach dashboard stays a single cheap query as attempt history grows.
    """

    __tablename__ = "concept_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "course_concept_id", name="uq_mastery_student_concept"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    course_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_concepts.id"), nullable=False
    )
    # Exponential moving average of correctness in [0, 1]: recent answers count
    # for more, so improvement shows up without discarding earlier evidence.
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
