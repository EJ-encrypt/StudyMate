"""cached explanations of how a Coach revision topic's concepts fit together

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topic_explanations",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("links", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_topic_explanations_course_id", "topic_explanations", ["course_id"])
    # Same reasoning as 0011: closed to Supabase's public REST API.
    op.execute('ALTER TABLE "topic_explanations" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table("topic_explanations")
