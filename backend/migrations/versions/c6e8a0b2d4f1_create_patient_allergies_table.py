"""create patient allergies table

Revision ID: c6e8a0b2d4f1
Revises: b4d6f8a2c1e3
Create Date: 2026-10-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c6e8a0b2d4f1'
down_revision: Union[str, Sequence[str], None] = 'b4d6f8a2c1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'allergies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('allergen', sa.String(length=200), nullable=False),
        sa.Column('reaction', sa.String(length=300), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('onset_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_allergies_patient_id'),
        'allergies',
        ['patient_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_allergies_patient_id'),
        table_name='allergies',
    )
    op.drop_table('allergies')
