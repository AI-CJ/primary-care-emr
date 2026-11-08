"""Record staff changes to follow-up task deadlines.

Revision ID: 6b3f2c1d9a80
Revises: a3d8f1c6e2b9
Create Date: 2026-11-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b3f2c1d9a80"
down_revision: Union[str, Sequence[str], None] = "a3d8f1c6e2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "follow_up_due_date_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id", sa.Integer(),
            sa.ForeignKey("follow_up_tasks.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("previous_due_date", sa.Date(), nullable=True),
        sa.Column("new_due_date", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_follow_up_due_date_changes_task_id",
        "follow_up_due_date_changes",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_follow_up_due_date_changes_task_id",
        table_name="follow_up_due_date_changes",
    )
    op.drop_table("follow_up_due_date_changes")
