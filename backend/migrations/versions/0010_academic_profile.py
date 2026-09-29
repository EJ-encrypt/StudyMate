"""academic profile, course level/semester, and course summaries

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: existing accounts have not been through onboarding, and a null
    # school is exactly how the app detects that.
    op.add_column("users", sa.Column("school", sa.String(150), nullable=True))
    op.add_column("users", sa.Column("programme", sa.String(150), nullable=True))
    op.add_column("users", sa.Column("level", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("semester", sa.Integer(), nullable=True))

    op.add_column("courses", sa.Column("level", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("courses", sa.Column("semester", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("courses", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "courses",
        sa.Column("documents_at_summary", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("courses", "documents_at_summary")
    op.drop_column("courses", "summary")
    op.drop_column("courses", "semester")
    op.drop_column("courses", "level")
    op.drop_column("users", "semester")
    op.drop_column("users", "level")
    op.drop_column("users", "programme")
    op.drop_column("users", "school")
