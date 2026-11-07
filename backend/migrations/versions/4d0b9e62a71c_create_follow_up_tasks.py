"""Create patient-specific follow-up tasks.

Revision ID: 4d0b9e62a71c
Revises: b7e2d9c4a610
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d0b9e62a71c"
down_revision: Union[str, Sequence[str], None] = "b7e2d9c4a610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "follow_up_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_follow_up_tasks_patient_id", "follow_up_tasks", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_follow_up_tasks_patient_id", table_name="follow_up_tasks")
    op.drop_table("follow_up_tasks")
