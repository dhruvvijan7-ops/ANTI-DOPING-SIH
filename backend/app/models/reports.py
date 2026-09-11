"""Investigation report model (STAGE I + Reporting gate).

Reports snapshot case information at a point in time. Versioning is row-based:
each publish/edit that changes a FINAL report creates a new version row and
supersedes the previous one.

Two storage representations coexist:

* ``document_blocks`` -- a stable, structured, JSON rich-text block array used by
  the in-app word-like editor (paragraphs, headings, lists, tables, quotes,
  page breaks). Each block carries provenance so AI-generated vs human-authored
  content stays distinguishable at the data level (§567).
* ``sections_json`` -- the legacy sectioned snapshot assembled from live case data
  (kept for backward compatibility and read-only views).

``report_type`` records whether a report is MANUAL, AI_ASSISTED or HYBRID.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
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

REPORT_STATUSES = ("DRAFT", "IN_REVIEW", "FINAL", "SUPERSEDED", "ARCHIVED")

REPORT_TYPES = ("MANUAL", "AI_ASSISTED", "HYBRID")

# Block kinds supported by the structured document editor.
BLOCK_TYPES = ("paragraph", "heading", "list", "table", "quote", "page_break")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"
    __table_args__ = (Index("ix_reports_case_version", "investigation_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(16), default="MANUAL", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False, index=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Structured rich-text blocks for the in-app word-like editor.
    document_blocks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Unsaved draft content for autosave; distinct from the last persisted version.
    draft_blocks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    draft_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    investigation: Mapped["Investigation"] = relationship("Investigation", backref="reports")