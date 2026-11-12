"""Track release of lab results to the patient portal preview.

Revision ID: b2d4e6f8a012
Revises: e1f6c8b0d2a9
Create Date: 2026-11-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2d4e6f8a012"
down_revision: Union[str, Sequence[str], None] = "e1f6c8b0d2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing results are withheld until explicitly released.
    op.add_column(
        "lab_results",
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lab_results", "released_at")
