"""Store patient-selected communication preferences for the synthetic portal.

Revision ID: b7f1e0a9c5d2
Revises: 7ae1f09c63b2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7f1e0a9c5d2"
down_revision: Union[str, Sequence[str], None] = "7ae1f09c63b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_communication_preferences",
        sa.Column("patient_id", sa.Integer(), primary_key=True),
        sa.Column("preferred_channel", sa.String(length=16),
                  nullable=False, server_default="portal"),
        sa.Column("appointment_reminders", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")),
        sa.Column("care_updates", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "preferred_channel IN ('portal', 'phone', 'email')",
            name="ck_patient_communication_preferred_channel",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("patient_communication_preferences")
