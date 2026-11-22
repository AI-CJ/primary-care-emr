"""Persist privacy-minimal authentication and clinical access events.

Revision ID: 7ae1f09c63b2
Revises: a0f9c4e2d681
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7ae1f09c63b2"
down_revision: Union[str, Sequence[str], None] = "a0f9c4e2d681"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("subject_patient_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("route_template", sa.String(length=160), nullable=False),
        sa.Column("http_method", sa.String(length=8), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('login_success', 'login_failure', 'logout', "
            "'clinical_read', 'clinical_write', 'access_denied')",
            name="ck_audit_events_event_type",
        ),
        sa.CheckConstraint(
            "status_code BETWEEN 100 AND 599", name="ck_audit_events_status_code",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["user_accounts.id"], ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_subject_patient_id", "audit_events", ["subject_patient_id"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_index("ix_audit_events_subject_patient_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_user_id", table_name="audit_events")
    op.drop_table("audit_events")
