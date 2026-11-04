"""Create specialist referral requests for synthetic visits.

Revision ID: b6a2c9f0d735
Revises: a9e7c6b5d401
Create Date: 2026-11-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6a2c9f0d735"
down_revision: Union[str, Sequence[str], None] = "a9e7c6b5d401"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(),
            sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("specialty", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_referrals_encounter_id", "referrals", ["encounter_id"])


def downgrade() -> None:
    op.drop_index("ix_referrals_encounter_id", table_name="referrals")
    op.drop_table("referrals")
