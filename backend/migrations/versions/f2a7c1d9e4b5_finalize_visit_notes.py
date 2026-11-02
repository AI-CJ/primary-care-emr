"""Allow finalized visit notes to become read-only.

Revision ID: f2a7c1d9e4b5
Revises: c9e4f7a1d2b3
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a7c1d9e4b5"
down_revision: Union[str, Sequence[str], None] = "c9e4f7a1d2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing visit notes remain drafts.
    op.add_column(
        "encounters",
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("encounters", "finalized_at")
