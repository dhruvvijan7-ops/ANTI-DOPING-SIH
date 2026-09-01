"""Relational relationship graph.

Relationships are stored relationally (directive §9) with a type lookup table.
Graph views are derived from these tables via SQL.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

SUBJECT_TYPES = ("ATHLETE", "SUPPORT_PERSON", "TEAM", "ORGANIZATION", "PROVIDER", "SUPPLEMENT")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class RelationshipType(Base):
    __tablename__ = "relationship_types"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    relationships: Mapped[list["EntityRelationship"]] = relationship(back_populates="rel_type")


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        Index("ix_rel_from", "from_entity_type", "from_entity_id"),
        Index("ix_rel_to", "to_entity_type", "to_entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    from_entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    from_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    relationship_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("relationship_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    to_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("intelligence_sources.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[str | None] = mapped_column("metadata", String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    rel_type: Mapped[RelationshipType] = relationship(back_populates="relationships", lazy="joined")
