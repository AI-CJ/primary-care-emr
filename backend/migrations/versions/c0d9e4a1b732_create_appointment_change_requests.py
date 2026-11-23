
"""Queue synthetic patient appointment change requests independently of visit history.

Revision ID: c0d9e4a1b732
Revises: b7f1e0a9c5d2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0d9e4a1b732"
down_revision: Union[str, Sequence[str], None] = "b7f1e0a9c5d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointment_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("kind IN ('cancel', 'reschedule')", name="ck_appointment_change_kind"),
        sa.CheckConstraint("status IN ('pending', 'reviewed')",
                           name="ck_appointment_change_status"),
    )
    op.create_index("ix_appointment_change_requests_appointment_id",
                    "appointment_change_requests", ["appointment_id"])
    op.create_index("ix_appointment_change_requests_patient_id",
                    "appointment_change_requests", ["patient_id"])
    op.create_index(
        "uq_appointment_change_requests_pending", "appointment_change_requests",
        ["appointment_id"], unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_appointment_change_requests_pending",
                  table_name="appointment_change_requests")
    op.drop_index("ix_appointment_change_requests_patient_id",
                  table_name="appointment_change_requests")
    op.drop_index("ix_appointment_change_requests_appointment_id",
                  table_name="appointment_change_requests")
    op.drop_table("appointment_change_requests")
