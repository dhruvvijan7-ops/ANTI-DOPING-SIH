"""Investigation report model (STAGE I).

Reports snapshot case information at a point in time. Versioning is row-based:
each publish/edit that changes a FINAL report creates a new version row and
supersedes the previous one. Sections are stored as JSON assembled from live case
data plus investigator-controlled text (purpose, outcome, unresolved questions).
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

REPORT_STATUSES = ("DRAFT", "FINAL", "SUPERSEDED")


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
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", nullable=False, index=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
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