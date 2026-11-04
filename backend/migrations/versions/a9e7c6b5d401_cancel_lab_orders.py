"""Record cancellations of pending synthetic lab requests.

Revision ID: a9e7c6b5d401
Revises: a8d4f2c6b901
Create Date: 2026-11-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9e7c6b5d401"
down_revision: Union[str, Sequence[str], None] = "a8d4f2c6b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lab_orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "lab_orders", sa.Column("cancellation_reason", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("lab_orders", "cancellation_reason")
    op.drop_column("lab_orders", "cancelled_at")
