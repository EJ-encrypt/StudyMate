"""serverless job queue, lecture timetable and reminders, arcade games, RLS

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every table the app owns. Supabase publishes the public schema through its
# REST API, reachable with the anon key that ships in the frontend bundle, so
# a table without row-level security is readable and writable by anyone on
# the internet. Enabling RLS with no policies closes that: the API connects
# as the table owner, which bypasses RLS, while the REST API gets nothing.
_TABLES = (
    "users",
    "courses",
    "enrollments",
    "lecture_documents",
    "course_concepts",
    "knowledge_concepts",
    "assessments",
    "assessment_items",
    "attempts",
    "attempt_answers",
    "concept_mastery",
    "student_progress",
    "earned_badges",
    "jobs",
    "lecture_slots",
    "push_subscriptions",
    "sent_reminders",
    "game_sessions",
    "alembic_version",
)


def upgrade() -> None:
    # Passwords move to Supabase Auth; existing hashes are kept, not dropped.
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)
    op.add_column(
        "users", sa.Column("timezone", sa.String(64), nullable=False, server_default="Africa/Accra")
    )
    op.add_column("users", sa.Column("notify_push", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("notify_email", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_student_id", "jobs", ["student_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "lecture_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("venue", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lecture_slots_student_id", "lecture_slots", ["student_id"])

    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_push_subscriptions_student_id", "push_subscriptions", ["student_id"])

    op.create_table(
        "sent_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lecture_slots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurs_on", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slot_id", "occurs_on", "kind", name="uq_sent_reminder"),
    )

    op.create_table(
        "game_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("game", sa.String(30), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("mistakes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_game_sessions_student_id", "game_sessions", ["student_id"])

    for table in _TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.drop_table("game_sessions")
    op.drop_table("sent_reminders")
    op.drop_table("push_subscriptions")
    op.drop_table("lecture_slots")
    op.drop_table("jobs")
    op.drop_column("users", "notify_email")
    op.drop_column("users", "notify_push")
    op.drop_column("users", "timezone")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
