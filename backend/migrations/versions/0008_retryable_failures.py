"""flag whether a failure is worth retrying

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("lecture_documents", "assessments"):
        op.add_column(
            table,
            sa.Column("can_retry", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    for table in ("lecture_documents", "assessments"):
        op.drop_column(table, "can_retry")
