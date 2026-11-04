"""Store a single immutable result for each synthetic lab request.

Revision ID: a8d4f2c6b901
Revises: f5c63e72a901
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8d4f2c6b901"
down_revision: Union[str, Sequence[str], None] = "f5c63e72a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lab_order_id", sa.Integer(),
            sa.ForeignKey("lab_orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("collected_on", sa.Date(), nullable=False),
        sa.Column("result_text", sa.Text(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("lab_order_id", name="uq_lab_results_order"),
    )


def downgrade() -> None:
    op.drop_table("lab_results")
