"""Create lab test requests for visit notes.

Revision ID: f5c63e72a901
Revises: e5a7b9c1d3f6
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5c63e72a901"
down_revision: Union[str, Sequence[str], None] = "e5a7b9c1d3f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(),
            sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("test_name", sa.String(length=200), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("clinical_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lab_orders_encounter_id", "lab_orders", ["encounter_id"])


def downgrade() -> None:
    op.drop_index("ix_lab_orders_encounter_id", table_name="lab_orders")
    op.drop_table("lab_orders")
