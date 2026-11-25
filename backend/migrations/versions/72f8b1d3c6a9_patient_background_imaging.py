"""Store patient background and historical imaging reports.

Revision ID: 72f8b1d3c6a9
Revises: 8bd420ea9f63
"""
from alembic import op
import sqlalchemy as sa

revision = "72f8b1d3c6a9"
down_revision = "8bd420ea9f63"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "patient_backgrounds",
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("reviewed_on", sa.Date(), nullable=False),
        sa.Column("medical_history", sa.Text(), nullable=False),
        sa.Column("surgical_history", sa.Text(), nullable=False),
        sa.Column("family_history", sa.Text(), nullable=False),
        sa.Column("social_history", sa.Text(), nullable=False),
        sa.Column("care_context", sa.Text(), nullable=False),
    )
    op.create_table(
        "imaging_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("reported_on", sa.Date(), nullable=False),
        sa.Column("modality", sa.String(40), nullable=False),
        sa.Column("study", sa.String(200), nullable=False),
        sa.Column("indication", sa.Text(), nullable=False),
        sa.Column("findings", sa.Text(), nullable=False),
        sa.Column("impression", sa.Text(), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("shared_on", sa.Date(), nullable=True),
        sa.CheckConstraint("reported_on >= performed_on", name="ck_imaging_report_chronology"),
        sa.CheckConstraint("shared_on IS NULL OR shared_on >= reported_on", name="ck_imaging_report_share_date"),
    )
    op.create_index("ix_imaging_reports_patient_id", "imaging_reports", ["patient_id"])


def downgrade():
    # Removing these tables would destroy recorded background and reports.
    for table in ("imaging_reports", "patient_backgrounds"):
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("Refusing to drop populated clinical history tables")
    op.drop_index("ix_imaging_reports_patient_id", table_name="imaging_reports")
    op.drop_table("imaging_reports")
    op.drop_table("patient_backgrounds")
