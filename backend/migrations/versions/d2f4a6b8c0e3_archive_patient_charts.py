"""Archive/reactivate synthetic patient charts without removing clinical history.

Revision ID: d2f4a6b8c0e3
Revises: c0d9e4a1b732
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2f4a6b8c0e3"
down_revision: Union[str, Sequence[str], None] = "c0d9e4a1b732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "patient_lifecycle_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_accounts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "action IN ('archive', 'reactivate')", name="ck_patient_lifecycle_action",
        ),
    )
    op.create_index(
        "ix_patient_lifecycle_events_patient_id", "patient_lifecycle_events", ["patient_id"],
    )
    op.create_index(
        "ix_patient_lifecycle_events_actor_user_id", "patient_lifecycle_events", ["actor_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_patient_lifecycle_events_actor_user_id", table_name="patient_lifecycle_events")
    op.drop_index("ix_patient_lifecycle_events_patient_id", table_name="patient_lifecycle_events")
    op.drop_table("patient_lifecycle_events")
    op.drop_column("patients", "archived_at")
