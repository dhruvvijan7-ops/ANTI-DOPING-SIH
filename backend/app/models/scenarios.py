"""Metadata for synthetic evaluation scenarios.

Each known scenario is assigned a stable identifier (e.g. SCENARIO_NORMAL_001) and
records the subjects involved so tests and the demo can retrieve and validate them.
These labels are for prototype evaluation only, not real-world ground truth.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class SyntheticScenario(Base):
    __tablename__ = "synthetic_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    scenario_ref: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    scenario_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    extra_refs: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
