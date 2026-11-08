"""Retain cancelled follow-up tasks and cancellation reasons.

Revision ID: a3d8f1c6e2b9
Revises: 9e6c2a1f8b40
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3d8f1c6e2b9"
down_revision: Union[str, Sequence[str], None] = "9e6c2a1f8b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("follow_up_tasks") as batch:
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("cancellation_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("follow_up_tasks") as batch:
        batch.drop_column("cancellation_reason")
        batch.drop_column("cancelled_at")
