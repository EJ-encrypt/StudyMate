"""usernames, tutorial progress, stored document text, concept match history

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(30), nullable=True))
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.add_column(
        "users",
        sa.Column("tutorial_seen", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("lecture_documents", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column("game_sessions", sa.Column("concept_ids", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("game_sessions", "concept_ids")
    op.drop_column("lecture_documents", "extracted_text")
    op.drop_column("users", "tutorial_seen")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
