"""investigations_and_reports

Revision ID: 0002_investigations_reports
Revises: 93e0ebdb044c
Create Date: 2026-09-07

Creates: investigations, evidence_items, investigation_tasks,
investigation_notes, investigation_findings, investigation_reports
and extends alerts with triage state + investigation link.
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_investigations_reports"
down_revision = "93e0ebdb044c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_ref", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("originating_alert_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["originating_alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigations_case_ref"), "investigations", ["case_ref"], unique=True)
    op.create_index("ix_investigations_subject", "investigations", ["subject_type", "subject_id"], unique=False)
    op.create_index("ix_investigations_status", "investigations", ["status", "created_at"], unique=False)
    op.create_index(op.f("ix_investigations_originating_alert_id"), "investigations", ["originating_alert_id"], unique=False)
    op.create_index(op.f("ix_investigations_assigned_to"), "investigations", ["assigned_to"], unique=False)

    # triage state on alerts + link to the investigation created from it
    op.add_column("alerts", sa.Column("investigation_id", sa.Uuid(), nullable=True))
    op.add_column("alerts", sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "alerts",
        sa.Column(
            "triage_meta_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.create_foreign_key("fk_alerts_investigation", "alerts", "investigations", ["investigation_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_alerts_investigation_id"), "alerts", ["investigation_id"], unique=False)

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("item_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("relationship_to_case", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_items_investigation_id"), "evidence_items", ["investigation_id"], unique=False)

    op.create_table(
        "investigation_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigation_tasks_assigned_to"), "investigation_tasks", ["assigned_to"], unique=False)
    op.create_index(op.f("ix_investigation_tasks_investigation_id"), "investigation_tasks", ["investigation_id"], unique=False)

    op.create_table(
        "investigation_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigation_notes_author_id"), "investigation_notes", ["author_id"], unique=False)
    op.create_index(op.f("ix_investigation_notes_investigation_id"), "investigation_notes", ["investigation_id"], unique=False)

    op.create_table(
        "investigation_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("supporting_evidence", sa.Text(), nullable=True),
        sa.Column("assessment", sa.String(length=32), nullable=True),
        sa.Column("confident", sa.Boolean(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigation_findings_author_id"), "investigation_findings", ["author_id"], unique=False)
    op.create_index(op.f("ix_investigation_findings_investigation_id"), "investigation_findings", ["investigation_id"], unique=False)

    op.create_table(
        "investigation_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("sections_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigation_reports_investigation_id"), "investigation_reports", ["investigation_id"], unique=False)


def downgrade() -> None:
    op.drop_table("investigation_reports")
    op.drop_table("investigation_findings")
    op.drop_table("investigation_notes")
    op.drop_table("investigation_tasks")
    op.drop_table("evidence_items")
    op.drop_index(op.f("ix_alerts_investigation_id"), table_name="alerts")
    op.drop_constraint("fk_alerts_investigation", "alerts", type_="foreignkey")
    op.drop_column("alerts", "triage_meta_json")
    op.drop_column("alerts", "triaged_at")
    op.drop_column("alerts", "investigation_id")
    op.drop_table("investigations")