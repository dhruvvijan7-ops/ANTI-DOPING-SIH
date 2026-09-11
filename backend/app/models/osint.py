"""OSINT subsystem domain models (gate §514 §688 §720 §735 §738 §763).

The OSINT subsystem has its own source registry (external real-world feeds/APIs),
its own raw record store (with full provenance), entity mentions and analyst
claims. Collected records are promoted into the intelligence domain as regular
IntelligenceReport rows (with provenance pointing back to the raw record), so one
can always trace a report -> osint_record -> original source URL/timestamp.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Health states (§48).
HEALTH_ACTIVE = "ACTIVE"
HEALTH_DEGRADED = "DEGRADED"
HEALTH_FAILED = "FAILED"
HEALTH_RATE_LIMITED = "RATE_LIMITED"
HEALTH_DISABLED = "DISABLED"
HEALTH_STATES = (
    HEALTH_ACTIVE,
    HEALTH_DEGRADED,
    HEALTH_FAILED,
    HEALTH_RATE_LIMITED,
    HEALTH_DISABLED,
)

# Claim verification states (§54).
CLAIM_UNREVIEWED = "UNREVIEWED"
CLAIM_REVIEWED = "REVIEWED"
CLAIM_CORROBORATED = "CORROBORATED"
CLAIM_DISPUTED = "DISPUTED"
CLAIM_REJECTED = "REJECTED"
CLAIM_PROMOTED_TO_EVIDENCE = "PROMOTED_TO_EVIDENCE"
CLAIM_STATES = (
    CLAIM_UNREVIEWED,
    CLAIM_REVIEWED,
    CLAIM_CORROBORATED,
    CLAIM_DISPUTED,
    CLAIM_REJECTED,
    CLAIM_PROMOTED_TO_EVIDENCE,
)

# Authority tiers (§30): OFFICIAL -> PUBLIC_NEWS -> PUBLIC_SOCIAL -> ARCHIVAL -> COMMERCIAL.
AUTHORITY_OFFICIAL = "OFFICIAL"
AUTHORITY_PUBLIC_NEWS = "PUBLIC_NEWS"
AUTHORITY_PUBLIC_SOCIAL = "PUBLIC_SOCIAL"
AUTHORITY_ARCHIVAL = "ARCHIVAL"
AUTHORITY_COMMERCIAL = "COMMERCIAL"
AUTHORITY_TIERS = (
    AUTHORITY_OFFICIAL,
    AUTHORITY_PUBLIC_NEWS,
    AUTHORITY_PUBLIC_SOCIAL,
    AUTHORITY_ARCHIVAL,
    AUTHORITY_COMMERCIAL,
)

# Duplicate detection reasons (§51).
DUP_CONTENT_HASH = "content_hash"
DUP_CANONICAL_URL = "canonical_url"
DUP_NORMALIZED_TITLE = "normalized_title"
DUP_REASONS = (DUP_CONTENT_HASH, DUP_CANONICAL_URL, DUP_NORMALIZED_TITLE)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class OsintSource(Base):
    """External source configuration (§47). Configuration only — never a fake payload."""

    __tablename__ = "osint_sources"
    __table_args__ = (
        Index("ix_osint_sources_enabled_type", "enabled", "connector_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    authority: Mapped[str] = mapped_column(String(32), default=AUTHORITY_PUBLIC_NEWS, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    poll_frequency_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    health: Mapped[str] = mapped_column(String(32), default=HEALTH_ACTIVE, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    records: Mapped[list["OsintRecord"]] = relationship(back_populates="source")


class OsintRecord(Base):
    """Raw collected record with full provenance (§49 §50)."""

    __tablename__ = "osint_records"
    __table_args__ = (
        Index("ix_osint_records_source_time", "source_id", "published_at"),
        Index("ix_osint_records_hash", "content_hash"),
        Index("ix_osint_records_canonical", "canonical_url"),
        Index("ix_osint_records_syndication", "syndication_group"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("osint_sources.id", ondelete="CASCADE"), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_level: Mapped[str] = mapped_column(String(32), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    syndication_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("osint_records.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    terms_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[OsintSource] = relationship(back_populates="records", lazy="joined")
    mentions: Mapped[list["OsintMention"]] = relationship(back_populates="record")
    claims: Mapped[list["OsintClaim"]] = relationship(back_populates="record")

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_of is not None


class OsintMention(Base):
    """An entity that appears in a collected record (grounded by DB subject rows)."""

    __tablename__ = "osint_mentions"
    __table_args__ = (
        Index("ix_osint_mentions_subject", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("osint_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    subject_label: Mapped[str] = mapped_column(String(255), nullable=False)
    match_kind: Mapped[str] = mapped_column(String(16), default="CONTAINS", nullable=False)

    record: Mapped[OsintRecord] = relationship(back_populates="mentions")


class OsintClaim(Base):
    """Analyst claim derived from a collected record (§53 §54)."""

    __tablename__ = "osint_claims"
    __table_args__ = (
        Index("ix_osint_claims_verification", "verification"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("osint_records.id", ondelete="CASCADE"), nullable=True
    )
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    subject_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    predicate: Mapped[str] = mapped_column(String(64), nullable=False)
    object_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification: Mapped[str] = mapped_column(String(32), default=CLAIM_UNREVIEWED, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    record: Mapped[OsintRecord | None] = relationship(back_populates="claims")


# Extra provenance columns promoted into intelligence reports (gate §58: URL,
# publisher, retrieval date, publication date).
INTELLIGENCE_REPORT_OSINT_COLUMNS = (
    "url",
    "publisher",
    "retrieved_at",
    "content_hash",
    "osint_record_id",
)


def published_date_of(published_at: datetime | None) -> date | None:
    """The report_date for a promoted report: the article publication date."""
    return published_at.date() if published_at else None