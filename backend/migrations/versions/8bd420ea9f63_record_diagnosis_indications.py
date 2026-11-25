"""Record ICD-10-CM diagnosis codes and selected clinical indications.

Revision ID: 8bd420ea9f63
Revises: d2f4a6b8c0e3
"""
from alembic import op
import sqlalchemy as sa

revision = "8bd420ea9f63"
down_revision = "d2f4a6b8c0e3"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("problems", "name", existing_type=sa.String(200), type_=sa.String(512))
    op.add_column("problems", sa.Column("icd10_code", sa.String(8), nullable=True))
    op.add_column("problems", sa.Column("icd10_title", sa.String(512), nullable=True))
    op.add_column("problems", sa.Column("icd10_release", sa.String(16), nullable=True))
    op.alter_column("encounter_problems", "problem_name_at_link", existing_type=sa.String(200), type_=sa.String(512))
    op.add_column("encounter_problems", sa.Column("icd10_code_at_link", sa.String(8), nullable=True))
    op.add_column("encounter_problems", sa.Column("icd10_release_at_link", sa.String(16), nullable=True))
    op.add_column("encounter_medications", sa.Column("indications_at_link", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    for table, parent, column, unique in (
        ("medication_indications", "medications", "medication_id", "uq_medication_indication"),
        ("lab_order_indications", "lab_orders", "lab_order_id", "uq_lab_order_indication"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(column, sa.Integer(), sa.ForeignKey(parent + ".id", ondelete="RESTRICT"), nullable=False),
            sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("problem_name", sa.String(512), nullable=False),
            sa.Column("icd10_code", sa.String(8), nullable=True),
            sa.Column("icd10_release", sa.String(16), nullable=True),
            sa.UniqueConstraint(column, "problem_id", name=unique),
        )
        op.create_index("ix_" + table + "_" + column, table, [column])
        op.create_index("ix_" + table + "_problem_id", table, ["problem_id"])


def downgrade():
    # Do not truncate longer clinical descriptions silently on a downgrade.
    op.drop_table("lab_order_indications")
    op.drop_table("medication_indications")
    op.drop_column("encounter_medications", "indications_at_link")
    op.drop_column("encounter_problems", "icd10_release_at_link")
    op.drop_column("encounter_problems", "icd10_code_at_link")
    op.alter_column("encounter_problems", "problem_name_at_link", existing_type=sa.String(512), type_=sa.String(200))
    op.drop_column("problems", "icd10_release")
    op.drop_column("problems", "icd10_title")
    op.drop_column("problems", "icd10_code")
    op.alter_column("problems", "name", existing_type=sa.String(512), type_=sa.String(200))
