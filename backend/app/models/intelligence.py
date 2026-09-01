"""Intelligence domain: sources, reports, assessments, tags.

Reports use generic subject_type/subject_id links so an intelligence record can be
associated with an athlete, support person, team, organization or provider.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Supported subject kinds for generic subject links.
SUBJECT_TYPES = ("ATHLETE", "SUPPORT_PERSON", "TEAM", "ORGANIZATION", "PROVIDER")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class IntelligenceSource(Base):
    __tablename__ = "intelligence_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reliability_default: Mapped[str] = mapped_column(String(8), default="C", nullable=False)
    confidentiality: Mapped[str] = mapped_column(String(32), default="INTERNAL", nullable=False)
    activity: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reports: Mapped[list["IntelligenceReport"]] = relationship(back_populates="source")


report_tags = Table(
    "report_tags",
    Base.metadata,
    Column(
        "report_id",
        Uuid(as_uuid=True),
        ForeignKey("intelligence_reports.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Uuid(as_uuid=True),
        ForeignKey("intelligence_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class IntelligenceReport(Base):
    __tablename__ = "intelligence_reports"
    __table_args__ = (
        Index("ix_intel_subject", "subject_type", "subject_id", "report_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("intelligence_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    ingestion_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    reliability: Mapped[str | None] = mapped_column(String(8), nullable=True)
    information_quality: Mapped[str | None] = mapped_column(String(8), nullable=True)
    confidentiality: Mapped[str] = mapped_column(String(32), default="INTERNAL", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="NEW", nullable=False, index=True)
    info_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source: Mapped[IntelligenceSource] = relationship(back_populates="reports", lazy="joined")
    assessments: Mapped[list["SourceAssessment"]] = relationship(back_populates="report")
    tags: Mapped[list["IntelligenceTag"]] = relationship(
        secondary=report_tags, back_populates="reports", lazy="selectin"
    )


class IntelligenceTag(Base):
    __tablename__ = "intelligence_tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reports: Mapped[list[IntelligenceReport]] = relationship(
        secondary=report_tags, back_populates="tags"
    )


class SourceAssessment(Base):
    __tablename__ = "source_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("intelligence_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("intelligence_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reliability: Mapped[str] = mapped_column(String(8), nullable=False)
    information_quality: Mapped[str] = mapped_column(String(8), nullable=False)
    assessment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped[IntelligenceReport] = relationship(back_populates="assessments")
