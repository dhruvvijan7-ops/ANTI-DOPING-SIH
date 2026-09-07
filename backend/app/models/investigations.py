"""Investigation workspace models (STAGE F/G).

An investigation is created when an alert is triaged (or directly). Everything in
this module is investigation metadata *owned by humans*: evidence, tasks, notes and
findings. Analytical data is preserved by reference (originating alert / subject),
never duplicated. Findings are statements decided by the investigator; analytical
scores are never auto-converted into findings.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

PRIORITY_LEVELS = ("LOW", "MODERATE", "HIGH", "VERY_HIGH", "CRITICAL")
INVESTIGATION_STATUSES = ("OPEN", "CLOSED", "ARCHIVED")
TASK_STATUSES = ("OPEN", "IN_PROGRESS", "DONE", "CANCELLED")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _case_ref() -> str:
    return f"CASE-{uuid.uuid4().hex[:10].upper()}"


class Investigation(Base):
    __tablename__ = "investigations"
    __table_args__ = (
        Index("ix_investigations_status", "status", "created_at"),
        Index("ix_investigations_subject", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    case_ref: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True, default=_case_ref
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default="OPEN", nullable=False, index=True
    )
    priority: Mapped[str] = mapped_column(String(16), default="MODERATE", nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    originating_alert_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    originating_alert: Mapped["Alert | None"] = relationship(
        "Alert", foreign_keys=[originating_alert_id], lazy="selectin"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", foreign_keys="Alert.investigation_id", back_populates="investigation", lazy="selectin"
    )
    evidence: Mapped[list["EvidenceItem"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["InvestigationTask"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    notes: Mapped[list["InvestigationNote"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )


class EvidenceItem(Base):
    """Recorded evidence attached to a case. Never fabricated; each row has a source
    and a classification so the investigator (not the engine) determines its weight."""

    __tablename__ = "evidence_items"
    __table_args__ = (Index("ix_evidence_case", "investigation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)  # DOCUMENT/TEST/SCREENSHOT/STATEMENT/OTHER
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), default="UNCLASSIFIED", nullable=False)
    item_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    relationship_to_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    investigation: Mapped[Investigation] = relationship(back_populates="evidence")


class InvestigationTask(Base):
    __tablename__ = "investigation_tasks"
    __table_args__ = (Index("ix_tasks_case_status", "investigation_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    investigation: Mapped[Investigation] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to], lazy="joined")


class InvestigationNote(Base):
    __tablename__ = "investigation_notes"
    __table_args__ = (Index("ix_notes_case", "investigation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    investigation: Mapped[Investigation] = relationship(back_populates="notes")
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id], lazy="joined")


class Finding(Base):
    """A finding is decided by the investigator, not derived automatically."""

    __tablename__ = "investigation_findings"
    __table_args__ = (Index("ix_findings_case", "investigation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(String(32), nullable=True)  # e.g. CONFIRMED/UNCONFIRMED/ASSESSED
    confident: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    investigation: Mapped[Investigation] = relationship(back_populates="findings")
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id], lazy="joined")