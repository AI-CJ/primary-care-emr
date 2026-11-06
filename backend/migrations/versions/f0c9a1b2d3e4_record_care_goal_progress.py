"""Record append-only progress entries for patient care goals.

Revision ID: f0c9a1b2d3e4
Revises: e8b2c4d6f0a1
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0c9a1b2d3e4"
down_revision: Union[str, Sequence[str], None] = "e8b2c4d6f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_goal_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "goal_id", sa.Integer(),
            sa.ForeignKey("care_goals.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_care_goal_progress_goal_id", "care_goal_progress", ["goal_id"])


def downgrade() -> None:
    op.drop_index("ix_care_goal_progress_goal_id", table_name="care_goal_progress")
    op.drop_table("care_goal_progress")
