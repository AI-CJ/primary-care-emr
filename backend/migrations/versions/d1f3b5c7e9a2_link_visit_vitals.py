"""Link recorded vital signs to visit notes with historical snapshots.

Revision ID: d1f3b5c7e9a2
Revises: e7b3c9d1a4f0
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1f3b5c7e9a2"
down_revision: Union[str, Sequence[str], None] = "e7b3c9d1a4f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounter_vitals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vital_id", sa.Integer(), sa.ForeignKey("vitals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recorded_on_at_link", sa.Date(), nullable=False),
        sa.Column("systolic_bp_at_link", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp_at_link", sa.Integer(), nullable=True),
        sa.Column("heart_rate_at_link", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate_at_link", sa.Integer(), nullable=True),
        sa.Column("temperature_c_at_link", sa.Float(), nullable=True),
        sa.Column("oxygen_saturation_at_link", sa.Integer(), nullable=True),
        sa.Column("height_cm_at_link", sa.Float(), nullable=True),
        sa.Column("weight_kg_at_link", sa.Float(), nullable=True),
        sa.Column("notes_at_link", sa.Text(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("encounter_id", "vital_id", name="uq_encounter_vitals_visit_vital"),
    )
    op.create_index("ix_encounter_vitals_vital_id", "encounter_vitals", ["vital_id"])


def downgrade() -> None:
    op.drop_index("ix_encounter_vitals_vital_id", table_name="encounter_vitals")
    op.drop_table("encounter_vitals")
