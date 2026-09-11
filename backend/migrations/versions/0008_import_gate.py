"""import gate: data_imports + import_rows with row-level provenance

Revision ID: 0008_import_gate
Revises: 0007_reporting_gate
Create Date: 2026-09-10

Import gate storage.  Each import is an auditable unit of work holding
raw original rows, normalized rows, per-field provenance, validation
errors/warnings, entity matches and dedupe keys alongside lifecycle
timestamps (conditions 11-26, 281-287, 596-607, 736-742).
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_import_gate"
down_revision = "0007_reporting_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target", sa.String(32), nullable=False, server_default="INTELLIGENCE"),
        sa.Column("source_kind", sa.String(16), nullable=False, server_default="FILE"),
        sa.Column("format", sa.String(16), nullable=True),
        sa.Column("source_filename", sa.String(255), nullable=True),
        sa.Column("file_hash", sa.String(128), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("payload", sa.LargeBinary(), nullable=True),
        sa.Column("sheet_name", sa.String(128), nullable=True),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("sheets", sa.JSON(), nullable=False),
        sa.Column("structure", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="UPLOADED"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_mapping", sa.JSON(), nullable=False),
        sa.Column("inferred_types", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_data_imports_owner_time"), "data_imports", ["created_by", "created_at"])
    op.create_index(op.f("ix_data_imports_source_kind"), "data_imports", ["source_kind"])
    op.create_index(op.f("ix_data_imports_format"), "data_imports", ["format"])
    op.create_index(op.f("ix_data_imports_file_hash"), "data_imports", ["file_hash"])
    op.create_index(op.f("ix_data_imports_status"), "data_imports", ["status"])

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("import_id", sa.Uuid(), sa.ForeignKey("data_imports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="READY"),
        sa.Column("original", sa.JSON(), nullable=False),
        sa.Column("normalized", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("field_provenance", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(512), nullable=True),
        sa.Column("entity_match", sa.JSON(), nullable=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("intelligence_reports.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index(op.f("ix_import_rows_import_number"), "import_rows", ["import_id", "row_number"])
    op.create_index(op.f("ix_import_rows_import_status"), "import_rows", ["import_id", "status"])
    op.create_index(op.f("ix_import_rows_dedupe"), "import_rows", ["import_id", "dedupe_key"])


def downgrade() -> None:
    op.drop_table("import_rows")
    op.drop_table("data_imports")