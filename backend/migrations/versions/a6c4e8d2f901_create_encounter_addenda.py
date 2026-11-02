"""Keep corrections to finalized visit notes in separate records.

Revision ID: a6c4e8d2f901
Revises: f2a7c1d9e4b5
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6c4e8d2f901"
down_revision: Union[str, Sequence[str], None] = "f2a7c1d9e4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounter_addenda",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id",
            sa.Integer(),
            sa.ForeignKey("encounters.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_encounter_addenda_encounter_id",
        "encounter_addenda",
        ["encounter_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_encounter_addenda_encounter_id", "encounter_addenda")
    op.drop_table("encounter_addenda")
