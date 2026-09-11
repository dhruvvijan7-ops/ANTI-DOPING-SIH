"""osint gate: source registry, raw records, mentions, claims + OSINT provenance on reports

Revision ID: 0009_osint_gate
Revises: 0008_import_gate
Create Date: 2026-09-11

OSINT gate storage (conditions 46-54, 243-254, 405, 463):
- osint_sources: external source CONFIGURATION (real URLs, connector type, health) -
  never fabricated articles.
- osint_records: raw collected records with full provenance (source_url, canonical_url,
  publisher, author, published_at, retrieved_at, content_hash, authority, extraction
  method) and dedupe/syndication markers.
- osint_mentions / osint_claims: grounded entity mentions and analyst claim model.
- intelligence_reports gains optional OSINT provenance columns (url, publisher,
  retrieved_at, content_hash, osint_record_id) so promoted records stay traceable.
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_osint_gate"
down_revision = "0008_import_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "osint_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(32), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("jurisdiction", sa.String(64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("poll_frequency_min", sa.Integer(), nullable=True),
        sa.Column("rate_limit_per_min", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("health", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_reason", sa.Text(), nullable=True),
        sa.Column("extra_config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ux_osint_sources_source_id"), "osint_sources", ["source_id"], unique=True)
    op.create_index(op.f("ix_osint_sources_enabled_type"), "osint_sources", ["enabled", "connector_type"])

    op.create_table(
        "osint_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("osint_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("canonical_url", sa.String(1024), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("authority_level", sa.String(32), nullable=False),
        sa.Column("extraction_method", sa.String(32), nullable=False),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("jurisdiction", sa.String(64), nullable=True),
        sa.Column("syndication_group", sa.String(64), nullable=True),
        sa.Column("duplicate_of", sa.Uuid(), sa.ForeignKey("osint_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("duplicate_reason", sa.String(32), nullable=True),
        sa.Column("terms_matched", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(op.f("ix_osint_records_source_time"), "osint_records", ["source_id", "published_at"])
    op.create_index(op.f("ix_osint_records_hash"), "osint_records", ["content_hash"])
    op.create_index(op.f("ix_osint_records_canonical"), "osint_records", ["canonical_url"])
    op.create_index(op.f("ix_osint_records_syndication"), "osint_records", ["syndication_group"])

    op.create_table(
        "osint_mentions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("osint_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("subject_label", sa.String(255), nullable=False),
        sa.Column("match_kind", sa.String(16), nullable=False, server_default="CONTAINS"),
    )
    op.create_index(op.f("ix_osint_mentions_record"), "osint_mentions", ["record_id"])
    op.create_index(op.f("ix_osint_mentions_subject"), "osint_mentions", ["subject_type", "subject_id"])

    op.create_table(
        "osint_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("osint_records.id", ondelete="CASCADE"), nullable=True),
        sa.Column("subject_type", sa.String(32), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("subject_label", sa.String(255), nullable=True),
        sa.Column("predicate", sa.String(64), nullable=False),
        sa.Column("object_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("verification", sa.String(32), nullable=False, server_default="UNREVIEWED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_osint_claims_record"), "osint_claims", ["record_id"])
    op.create_index(op.f("ix_osint_claims_verification"), "osint_claims", ["verification"])

    op.add_column(
        "intelligence_reports",
        sa.Column("url", sa.String(1024), nullable=True),
    )
    op.add_column(
        "intelligence_reports",
        sa.Column("canonical_url", sa.String(1024), nullable=True),
    )
    op.add_column(
        "intelligence_reports",
        sa.Column("publisher", sa.String(255), nullable=True),
    )
    op.add_column(
        "intelligence_reports",
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "intelligence_reports",
        sa.Column("content_hash", sa.String(128), nullable=True),
    )
    op.add_column(
        "intelligence_reports",
        sa.Column("osint_record_id", sa.Uuid(), sa.ForeignKey("osint_records.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index(op.f("ix_intelligence_reports_osint_record"), "intelligence_reports", ["osint_record_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_intelligence_reports_osint_record"), table_name="intelligence_reports")
    op.drop_column("intelligence_reports", "osint_record_id")
    op.drop_column("intelligence_reports", "content_hash")
    op.drop_column("intelligence_reports", "retrieved_at")
    op.drop_column("intelligence_reports", "publisher")
    op.drop_column("intelligence_reports", "canonical_url")
    op.drop_column("intelligence_reports", "url")
    op.drop_table("osint_claims")
    op.drop_table("osint_mentions")
    op.drop_table("osint_records")
    op.drop_table("osint_sources")