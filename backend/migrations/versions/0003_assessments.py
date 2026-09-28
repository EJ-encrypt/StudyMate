"""assessments, items and attempts

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: the types are created explicitly in upgrade(); without
# this create_table() would emit a second CREATE TYPE and fail.
item_kind = postgresql.ENUM("flashcard", "mcq", "fill_blank", name="item_kind", create_type=False)
assessment_status = postgresql.ENUM(
    "pending", "processing", "completed", "failed", name="assessment_status", create_type=False
)


def upgrade() -> None:
    item_kind.create(op.get_bind(), checkfirst=True)
    assessment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lecture_documents.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("kind", item_kind, nullable=False),
        sa.Column("status", assessment_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "assessment_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", item_kind, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "attempt_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column(
            "item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessment_items.id"), nullable=False
        ),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("attempt_answers")
    op.drop_table("attempts")
    op.drop_table("assessment_items")
    op.drop_table("assessments")
    assessment_status.drop(op.get_bind(), checkfirst=True)
    item_kind.drop(op.get_bind(), checkfirst=True)
