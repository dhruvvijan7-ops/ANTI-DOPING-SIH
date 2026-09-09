"""evidence_integrity_assignment

Revision ID: 0003_evidence_integrity
Revises: 0002_investigations_reports
Create Date: 2026-09-09

Phase D/E hardening: investigation assignment (enforced INVESTIGATIONS_ASSIGN),
evidence sensitivity/integrity/version history, structured finding->evidence
links with controlled delete behavior.

- evidence_items: + sensitivity, sha256_hash, version, deleted_at, deleted_by
- new evidence_versions: append-only snapshots (v1 at creation, one per update)
- new finding_evidence_links: FK-backed finding <-> evidence association
  (finding FK CASCADE, evidence FK RESTRICT so linked evidence cannot be
  hard-deleted; the API path is a controlled soft delete).
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_evidence_integrity"
down_revision = "0002_investigations_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- evidence_items: integrity + sensitivity + soft delete -----------------
    op.add_column(
        "evidence_items",
        sa.Column("sensitivity", sa.String(length=32), nullable=False, server_default="ROUTINE"),
    )
    op.add_column("evidence_items", sa.Column("sha256_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "evidence_items",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("evidence_items", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("evidence_items", sa.Column("deleted_by", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_evidence_items_deleted_by", "evidence_items", "users", ["deleted_by"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_evidence_items_sensitivity"), "evidence_items", ["sensitivity"], unique=False)
    op.create_index(op.f("ix_evidence_items_deleted_at"), "evidence_items", ["deleted_at"], unique=False)

    # --- evidence_versions (append-only history) -------------------------------
    op.create_table(
        "evidence_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=True),
        sa.Column("item_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("relationship_to_case", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column("change_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_versions_evidence",
        "evidence_versions",
        ["evidence_id", "version_number"],
        unique=True,
    )
    op.create_index(op.f("ix_evidence_versions_evidence_id"), "evidence_versions", ["evidence_id"], unique=False)

    # --- finding_evidence_links (FK-backed attribution) ------------------------
    op.create_table(
        "finding_evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("validity", sa.String(length=16), nullable=False, server_default="SUPPORTING"),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["finding_id"], ["investigation_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finding_evidence_link",
        "finding_evidence_links",
        ["finding_id", "evidence_id"],
        unique=True,
    )
    op.create_index(
        "ix_finding_evidence_evidence",
        "finding_evidence_links",
        ["evidence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("finding_evidence_links")
    op.drop_table("evidence_versions")
    op.drop_index(op.f("ix_evidence_items_deleted_at"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_sensitivity"), table_name="evidence_items")
    op.drop_constraint("fk_evidence_items_deleted_by", "evidence_items", type_="foreignkey")
    op.drop_column("evidence_items", "deleted_by")
    op.drop_column("evidence_items", "deleted_at")
    op.drop_column("evidence_items", "version")
    op.drop_column("evidence_items", "sha256_hash")
    op.drop_column("evidence_items", "sensitivity")