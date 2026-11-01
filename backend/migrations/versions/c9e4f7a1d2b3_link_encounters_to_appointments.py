"""Link visit notes to appointments when applicable.

Revision ID: c9e4f7a1d2b3
Revises: 1b3d5f7a9c2e
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e4f7a1d2b3"
down_revision: Union[str, Sequence[str], None] = "1b3d5f7a9c2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Historical visit notes were standalone; do not guess a matching visit.
    with op.batch_alter_table("encounters") as batch:
        batch.add_column(sa.Column("appointment_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_encounters_appointment_id",
            "appointments",
            ["appointment_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_encounters_appointment_id", ["appointment_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.drop_constraint(
            "uq_encounters_appointment_id", type_="unique"
        )
        batch.drop_constraint(
            "fk_encounters_appointment_id", type_="foreignkey"
        )
        batch.drop_column("appointment_id")
