"""per-concept mastery for the study coach

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_items",
        sa.Column(
            "course_concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("course_concepts.id"),
            nullable=True,
        ),
    )

    op.create_table(
        "concept_mastery",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column(
            "course_concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("course_concepts.id"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("student_id", "course_concept_id", name="uq_mastery_student_concept"),
    )
    op.create_index("ix_mastery_student_course", "concept_mastery", ["student_id", "course_id"])


def downgrade() -> None:
    op.drop_index("ix_mastery_student_course", table_name="concept_mastery")
    op.drop_table("concept_mastery")
    op.drop_column("assessment_items", "course_concept_id")
