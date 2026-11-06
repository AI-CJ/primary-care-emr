"""Record when a patient care goal is discontinued without marking it achieved.

Revision ID: b7e2d9c4a610
Revises: f0c9a1b2d3e4
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2d9c4a610"
down_revision: Union[str, Sequence[str], None] = "f0c9a1b2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "care_goals",
        sa.Column("discontinued_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "care_goals",
        sa.Column("discontinuation_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("care_goals", "discontinuation_reason")
    op.drop_column("care_goals", "discontinued_at")
