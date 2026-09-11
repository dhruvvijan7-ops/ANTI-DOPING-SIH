"""reporting_gate

Revision ID: 0007_reporting_gate
Revises: 0006_graph_gate
Create Date: 2026-09-10

Adds structured report document support:
report_type, document_blocks, draft_blocks, draft_saved_at, published_at.
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_reporting_gate"
down_revision = "0006_graph_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investigation_reports",
        sa.Column("report_type", sa.String(length=16), nullable=False, server_default="MANUAL"),
    )
    op.add_column(
        "investigation_reports",
        sa.Column("document_blocks", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "investigation_reports",
        sa.Column("draft_blocks", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "investigation_reports",
        sa.Column("draft_saved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "investigation_reports",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_investigation_reports_report_type"), "investigation_reports", ["report_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_investigation_reports_report_type"), table_name="investigation_reports")
    op.drop_column("investigation_reports", "published_at")
    op.drop_column("investigation_reports", "draft_saved_at")
    op.drop_column("investigation_reports", "draft_blocks")
    op.drop_column("investigation_reports", "document_blocks")
    op.drop_column("investigation_reports", "report_type")