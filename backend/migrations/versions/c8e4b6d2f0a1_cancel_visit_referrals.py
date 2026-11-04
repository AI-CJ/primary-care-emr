"""Keep cancelled referral requests in the visit record.

Revision ID: c8e4b6d2f0a1
Revises: b6a2c9f0d735
Create Date: 2026-11-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8e4b6d2f0a1"
down_revision: Union[str, Sequence[str], None] = "b6a2c9f0d735"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "referrals", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "referrals", sa.Column("cancellation_reason", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("referrals", "cancellation_reason")
    op.drop_column("referrals", "cancelled_at")
