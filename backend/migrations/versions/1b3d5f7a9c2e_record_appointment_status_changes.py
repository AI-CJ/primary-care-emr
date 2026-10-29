"""Record appointment status changes

Revision ID: 1b3d5f7a9c2e
Revises: f4b6d8a0c2e5
Create Date: 2026-10-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b3d5f7a9c2e"
down_revision: Union[str, Sequence[str], None] = "f4b6d8a0c2e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing appointments predate tracking; do not invent past events.
    op.create_table(
        "appointment_status_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_appointment_status_changes_appointment_id"),
        "appointment_status_changes",
        ["appointment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_appointment_status_changes_appointment_id"),
        table_name="appointment_status_changes",
    )
    op.drop_table("appointment_status_changes")
