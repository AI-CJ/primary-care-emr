"""Create staff and patient sign-in identities.

Revision ID: f6d2a4c8e901
Revises: b2d4e6f8a012
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6d2a4c8e901"
down_revision: Union[str, Sequence[str], None] = "b2d4e6f8a012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=20), nullable=False),
        sa.Column("staff_role", sa.String(length=20), nullable=True),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint(
            "(account_type = 'staff' AND staff_role IS NOT NULL "
            "AND staff_role IN ('admin', 'clinician', 'front_desk') "
            "AND patient_id IS NULL) OR (account_type = 'patient' "
            "AND staff_role IS NULL AND patient_id IS NOT NULL)",
            name="ck_user_accounts_role_scope",
        ),
        sa.CheckConstraint("username = lower(username)", name="ck_user_accounts_username_lower"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("patient_id", name="uq_user_accounts_patient_id"),
    )


def downgrade() -> None:
    op.drop_table("user_accounts")
