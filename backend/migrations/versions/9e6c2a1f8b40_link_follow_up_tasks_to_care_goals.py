"""Allow follow-up tasks to be associated with patient care goals.

Revision ID: 9e6c2a1f8b40
Revises: 4d0b9e62a71c
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e6c2a1f8b40"
down_revision: Union[str, Sequence[str], None] = "4d0b9e62a71c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("follow_up_tasks") as batch:
        batch.add_column(sa.Column("care_goal_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_follow_up_tasks_care_goal_id",
            "care_goals",
            ["care_goal_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_follow_up_tasks_care_goal_id", ["care_goal_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("follow_up_tasks") as batch:
        batch.drop_index("ix_follow_up_tasks_care_goal_id")
        batch.drop_constraint(
            "fk_follow_up_tasks_care_goal_id", type_="foreignkey"
        )
        batch.drop_column("care_goal_id")
