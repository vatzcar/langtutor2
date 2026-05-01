"""add persona idle_video_url column

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-05-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "personas",
        sa.Column("idle_video_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("personas", "idle_video_url")
