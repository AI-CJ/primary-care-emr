"""Record specialist follow-up for completed referral requests.

Revision ID: d5a9e1b7c3f0
Revises: c8e4b6d2f0a1
Create Date: 2026-11-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5a9e1b7c3f0"
down_revision: Union[str, Sequence[str], None] = "c8e4b6d2f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "referrals", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("referrals", sa.Column("seen_on", sa.Date(), nullable=True))
    op.add_column(
        "referrals", sa.Column("follow_up_summary", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("referrals", "follow_up_summary")
    op.drop_column("referrals", "seen_on")
    op.drop_column("referrals", "completed_at")
