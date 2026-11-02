"""Link chart problems to visit notes with a historical label snapshot.

Revision ID: e7b3c9d1a4f0
Revises: a6c4e8d2f901
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7b3c9d1a4f0"
down_revision: Union[str, Sequence[str], None] = "a6c4e8d2f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounter_problems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("problem_name_at_link", sa.String(length=200), nullable=False),
        sa.Column("problem_status_at_link", sa.String(length=20), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("encounter_id", "problem_id", name="uq_encounter_problems_visit_problem"),
    )
    op.create_index("ix_encounter_problems_problem_id", "encounter_problems", ["problem_id"])


def downgrade() -> None:
    op.drop_index("ix_encounter_problems_problem_id", table_name="encounter_problems")
    op.drop_table("encounter_problems")
