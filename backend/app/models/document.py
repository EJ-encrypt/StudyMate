import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LectureDocument(Base):
    __tablename__ = "lecture_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # values_callable keeps the lowercase member *values* in Postgres; without it
    # SQLAlchemy would persist member names ("PENDING") and break the enum type.
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Whether the failure was transient, so the UI can offer a retry rather
    # than leaving the student stuck on a dead end.
    can_retry: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    concepts: Mapped[list["KnowledgeConcept"]] = relationship(back_populates="document")


class CourseConcept(Base):
    """One canonical entry in a student's cumulative knowledge base for a course.

    Document-level KnowledgeConcept rows keep what each lecture actually said;
    these are the de-duplicated concepts built from them, which is what the
    cumulative quizzes and (in Phase 5) mastery tracking key off.
    """

    __tablename__ = "course_concepts"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "name", name="uq_course_concept_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored as JSONB rather than a pgvector column: a course holds a few
    # hundred concepts, so similarity is computed in Python and no extension
    # or index is needed yet (PROJECT_PLAN.md left pgvector conditional).
    embedding: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    # Which model produced the vector above. Vectors from different models have
    # different geometry and often different dimensions, so similarity is only
    # ever computed between concepts sharing this value.
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    mentions: Mapped[list["KnowledgeConcept"]] = relationship(back_populates="course_concept")


class KnowledgeConcept(Base):
    __tablename__ = "knowledge_concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lecture_documents.id"), nullable=False)
    course_concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_concepts.id"), nullable=True
    )
    # Denormalized alongside document_id so cumulative per-(student, course)
    # queries in Phase 4 don't need a join through lecture_documents.
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["LectureDocument"] = relationship(back_populates="concepts")
    course_concept: Mapped["CourseConcept | None"] = relationship(back_populates="mentions")
