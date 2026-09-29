"""cumulative course knowledge base

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "course_id", "name", name="uq_course_concept_name"),
    )
    op.create_index(
        "ix_course_concepts_student_course", "course_concepts", ["student_id", "course_id"]
    )

    op.add_column(
        "knowledge_concepts",
        sa.Column(
            "course_concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("course_concepts.id"),
            nullable=True,
        ),
    )

    # Cumulative assessments have no single source document.
    op.alter_column("assessments", "document_id", existing_type=postgresql.UUID(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM assessments WHERE document_id IS NULL")
    op.alter_column("assessments", "document_id", existing_type=postgresql.UUID(), nullable=False)
    op.drop_column("knowledge_concepts", "course_concept_id")
    op.drop_index("ix_course_concepts_student_course", table_name="course_concepts")
    op.drop_table("course_concepts")
