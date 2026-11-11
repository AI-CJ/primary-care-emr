"""Save instructions intended for patients with draft visit notes.

Revision ID: e1f6c8b0d2a9
Revises: 6b3f2c1d9a80
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f6c8b0d2a9"
down_revision: Union[str, Sequence[str], None] = "6b3f2c1d9a80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "encounters",
        sa.Column("patient_instructions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("encounters", "patient_instructions")
