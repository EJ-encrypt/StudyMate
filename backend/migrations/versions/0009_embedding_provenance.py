"""record which model produced each concept embedding

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows were all produced by the Gemini embedding model, which was
    # the only one available before provider fallback.
    op.add_column(
        "course_concepts",
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=False,
            server_default="gemini:gemini-embedding-2:768",
        ),
    )


def downgrade() -> None:
    op.drop_column("course_concepts", "embedding_model")
