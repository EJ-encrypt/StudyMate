"""short-answer items and exam papers

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres 12+ allows ADD VALUE inside a transaction as long as the new
    # value is not used in that same transaction; nothing here inserts it.
    op.execute("ALTER TYPE item_kind ADD VALUE IF NOT EXISTS 'short_answer'")

    # assessments.kind widens to its own type: an exam mixes item kinds, so it
    # is not itself an item kind.
    op.execute(
        "CREATE TYPE assessment_kind AS ENUM "
        "('flashcard', 'mcq', 'fill_blank', 'short_answer', 'exam')"
    )
    op.execute("ALTER TABLE assessments ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE assessments ALTER COLUMN kind TYPE assessment_kind "
        "USING kind::text::assessment_kind"
    )
    op.execute("ALTER TABLE assessments ALTER COLUMN status SET DEFAULT 'pending'")


def downgrade() -> None:
    # Any assessment that used a kind absent from item_kind must go before the
    # column can narrow back.
    op.execute("DELETE FROM assessments WHERE kind IN ('exam', 'short_answer')")
    op.execute(
        "ALTER TABLE assessments ALTER COLUMN kind TYPE item_kind USING kind::text::item_kind"
    )
    op.execute("DROP TYPE assessment_kind")
    # item_kind keeps 'short_answer': Postgres cannot drop a single enum label.
