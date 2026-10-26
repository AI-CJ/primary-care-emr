"""create patient vitals table

Revision ID: d8f0a2c4e6b1
Revises: c6e8a0b2d4f1
Create Date: 2026-10-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8f0a2c4e6b1'
down_revision: Union[str, Sequence[str], None] = 'c6e8a0b2d4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'vitals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('recorded_on', sa.Date(), nullable=False),
        sa.Column('systolic_bp', sa.Integer(), nullable=True),
        sa.Column('diastolic_bp', sa.Integer(), nullable=True),
        sa.Column('heart_rate', sa.Integer(), nullable=True),
        sa.Column('respiratory_rate', sa.Integer(), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('oxygen_saturation', sa.Integer(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_vitals_patient_id'),
        'vitals',
        ['patient_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_vitals_patient_id'),
        table_name='vitals',
    )
    op.drop_table('vitals')
