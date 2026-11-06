"""Create longitudinal patient care goals.

Revision ID: e8b2c4d6f0a1
Revises: d5a9e1b7c3f0
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b2c4d6f0a1"
down_revision: Union[str, Sequence[str], None] = "d5a9e1b7c3f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(),
            sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_care_goals_patient_id", "care_goals", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_care_goals_patient_id", table_name="care_goals")
    op.drop_table("care_goals")
