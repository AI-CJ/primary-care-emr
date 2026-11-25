"""Add medication reference identifiers and immunization events.

Revision ID: 9e25c4b7d810
Revises: 72f8b1d3c6a9
"""
from alembic import op
import sqlalchemy as sa

revision = "9e25c4b7d810"
down_revision = "72f8b1d3c6a9"
branch_labels = None
depends_on = None


def upgrade():
    for table, suffix in (("medications", ""), ("encounter_medications", "_at_link")):
        for name, length in (("rxnorm_cui", 20), ("rxnorm_release", 32), ("rxnorm_kind", 12)):
            op.add_column(table, sa.Column(name + suffix, sa.String(length), nullable=True))
    op.create_table(
        "immunizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cvx_code", sa.String(3), nullable=False),
        sa.Column("vaccine_name", sa.Text(), nullable=False),
        sa.Column("cvx_release", sa.String(64), nullable=False),
        sa.Column("administered_on", sa.Date(), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("manufacturer_code", sa.String(3)),
        sa.Column("manufacturer_name", sa.String(200)),
        sa.Column("mvx_release", sa.String(64)),
        sa.Column("lot_number", sa.String(100)),
        sa.Column("dose_number", sa.Integer()),
        sa.Column("route", sa.String(80)),
        sa.Column("site", sa.String(80)),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("void_reason", sa.Text()),
        sa.CheckConstraint("source IN ('clinic', 'historical_record', 'patient_reported')", name="ck_immunization_source"),
        sa.CheckConstraint("dose_number IS NULL OR dose_number > 0", name="ck_immunization_dose"),
        sa.CheckConstraint("(voided_at IS NULL AND void_reason IS NULL) OR (voided_at IS NOT NULL AND void_reason IS NOT NULL)", name="ck_immunization_void"),
    )
    op.create_index("ix_immunizations_patient_id", "immunizations", ["patient_id"])
    op.create_index("uq_immunization_active_event", "immunizations",
                    ["patient_id", "cvx_code", "administered_on"], unique=True,
                    postgresql_where=sa.text("voided_at IS NULL"), sqlite_where=sa.text("voided_at IS NULL"))


def downgrade():
    bind = op.get_bind()
    for table, predicate in (("immunizations", "1=1"), ("medications", "rxnorm_cui IS NOT NULL"),
                             ("encounter_medications", "rxnorm_cui_at_link IS NOT NULL")):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE {predicate} LIMIT 1")).first():
            raise RuntimeError("Refusing to discard recorded immunization or medication code history")
    op.drop_table("immunizations")
    for table, suffix in (("medications", ""), ("encounter_medications", "_at_link")):
        for name in ("rxnorm_cui", "rxnorm_release", "rxnorm_kind"):
            op.drop_column(table, name + suffix)
