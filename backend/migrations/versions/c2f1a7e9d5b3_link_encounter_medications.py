"""Link chart medications to visit notes with historical snapshots.

Revision ID: c2f1a7e9d5b3
Revises: d1f3b5c7e9a2
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f1a7e9d5b3"
down_revision: Union[str, Sequence[str], None] = "d1f3b5c7e9a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounter_medications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("medication_id", sa.Integer(), sa.ForeignKey("medications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name_at_link", sa.String(length=200), nullable=False),
        sa.Column("strength_at_link", sa.String(length=100), nullable=True),
        sa.Column("dose_at_link", sa.String(length=100), nullable=True),
        sa.Column("route_at_link", sa.String(length=100), nullable=True),
        sa.Column("frequency_at_link", sa.String(length=100), nullable=True),
        sa.Column("status_at_link", sa.String(length=20), nullable=False),
        sa.Column("start_date_at_link", sa.Date(), nullable=True),
        sa.Column("end_date_at_link", sa.Date(), nullable=True),
        sa.Column("instructions_at_link", sa.Text(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("encounter_id", "medication_id", name="uq_encounter_medications_visit_medication"),
    )
    op.create_index("ix_encounter_medications_medication_id", "encounter_medications", ["medication_id"])


def downgrade() -> None:
    op.drop_index("ix_encounter_medications_medication_id", table_name="encounter_medications")
    op.drop_table("encounter_medications")
