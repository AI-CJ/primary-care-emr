"""Link chart allergies to visit notes with historical snapshots.

Revision ID: e5a7b9c1d3f6
Revises: c2f1a7e9d5b3
Create Date: 2026-11-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5a7b9c1d3f6"
down_revision: Union[str, Sequence[str], None] = "c2f1a7e9d5b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounter_allergies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("allergy_id", sa.Integer(), sa.ForeignKey("allergies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("allergen_at_link", sa.String(length=200), nullable=False),
        sa.Column("reaction_at_link", sa.String(length=300), nullable=True),
        sa.Column("severity_at_link", sa.String(length=20), nullable=False),
        sa.Column("status_at_link", sa.String(length=20), nullable=False),
        sa.Column("onset_date_at_link", sa.Date(), nullable=True),
        sa.Column("notes_at_link", sa.Text(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("encounter_id", "allergy_id", name="uq_encounter_allergies_visit_allergy"),
    )
    op.create_index("ix_encounter_allergies_allergy_id", "encounter_allergies", ["allergy_id"])


def downgrade() -> None:
    op.drop_index("ix_encounter_allergies_allergy_id", table_name="encounter_allergies")
    op.drop_table("encounter_allergies")
