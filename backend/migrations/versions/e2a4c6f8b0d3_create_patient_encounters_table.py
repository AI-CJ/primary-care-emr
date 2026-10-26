"""create patient encounters table

Revision ID: e2a4c6f8b0d3
Revises: d8f0a2c4e6b1
Create Date: 2026-10-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2a4c6f8b0d3"
down_revision: Union[str, Sequence[str], None] = "d8f0a2c4e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "encounters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("reason_for_visit", sa.String(length=200), nullable=False),
        sa.Column("subjective", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_encounters_patient_id"),
        "encounters",
        ["patient_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_encounters_patient_id"),
        table_name="encounters",
    )
    op.drop_table("encounters")
