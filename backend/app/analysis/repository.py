"""Database -> analytic dataset bridge (pipeline intake stage).

Loads every analytic subject together with its signals (events and intelligence
reports) and relational graph edges, producing :class:`SubjectData` instances.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.contracts import RelationshipEdge, Signal, SubjectData
from app.analysis.features import reliability_weight
from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.intelligence import IntelligenceReport
from app.models.relationships import EntityRelationship, RelationshipType
from app.models.subjects import Athlete


def _report_signals(db: Session, athletes: list[uuid.UUID]) -> list[tuple[uuid.UUID, Signal]]:
    rows = db.scalars(
        select(IntelligenceReport).where(
            IntelligenceReport.subject_type == "ATHLETE",
            IntelligenceReport.subject_id.in_(athletes),
        )
    ).all()
    out: list[tuple[uuid.UUID, Signal]] = []
    for r in rows:
        reported_on = r.report_date or r.ingestion_date.date()
        source = r.source
        source_category = (source.source_type if source else None) or "UNKNOWN"
        weight = reliability_weight(r.reliability or (source.reliability_default if source else ""))
        out.append(
            (
                r.subject_id,
                Signal(
                    signal_id=r.id,
                    category="REPORT",
                    occurred_on=reported_on,
                    source_id=r.source_id,
                    source_category=source_category,
                    info_category=r.info_category,
                    weight=weight,
                    dedupe_key=r.dedupe_key,
                    raw_model="intelligence_reports",
                    raw_ref={
                        "reliability": r.reliability or (source.reliability_default if source else None),
                        "info_category": r.info_category,
                        "is_duplicate": r.is_duplicate,
                        "status": r.status,
                    },
                ),
            )
        )
    return out


def _event_signals(
    db: Session,
    athletes: list[uuid.UUID],
    model,
    category: str,
    date_attr: str,
    **ref_fields: str,
) -> list[tuple[uuid.UUID, Signal]]:
    rows = db.scalars(
        select(model).where(model.athlete_id.in_(athletes))  # type: ignore[attr-defined]
    ).all()
    out: list[tuple[uuid.UUID, Signal]] = []
    for row in rows:
        occurred = getattr(row, date_attr)
        if occurred is None:
            continue
        source = getattr(row, "source", None)
        source_category = (source.source_type if source else None) or "UNKNOWN"
        out.append(
            (
                row.athlete_id,
                Signal(
                    signal_id=row.id,
                    category=category,
                    occurred_on=occurred,
                    source_id=getattr(row, "source_id", None),
                    source_category=source_category,
                    weight=1.0,
                    raw_model=model.__tablename__,
                    raw_ref={k: getattr(row, v, None) for k, v in ref_fields.items()},
                ),
            )
        )
    return out


def _relationship_edges(db: Session, athletes: list[uuid.UUID]) -> dict[uuid.UUID, list[RelationshipEdge]]:
    rows = db.scalars(
        select(EntityRelationship).where(
            (EntityRelationship.from_entity_type == "ATHLETE")
            & (EntityRelationship.from_entity_id.in_(athletes))
            | (EntityRelationship.to_entity_type == "ATHLETE")
            & (EntityRelationship.to_entity_id.in_(athletes))
        )
    ).all()
    out: dict[uuid.UUID, list[RelationshipEdge]] = {}
    for row in rows:
        edge_type = row.rel_type.name if row.rel_type else "UNKNOWN"
        weight = row.confidence if row.confidence is not None else 1.0
        if row.from_entity_type == "ATHLETE":
            subject_id = row.from_entity_id
            direction = "OUT"
            other_type, other_id = row.to_entity_type, row.to_entity_id
        else:
            subject_id = row.to_entity_id
            direction = "IN"
            other_type, other_id = row.from_entity_type, row.from_entity_id
        out.setdefault(subject_id, []).append(
            RelationshipEdge(
                edge_type=edge_type,
                direction=direction,
                weight=weight,
                other_subject_type=other_type,
                other_subject_id=other_id,
                raw_ref={"from": str(row.from_entity_id), "to": str(row.to_entity_id)},
            )
        )
    return out


def load_subjects(db: Session, subject_ids: list[uuid.UUID] | None = None) -> list[SubjectData]:
    """Load all analytic subjects (athletes) with their signals and edges."""
    stmt = select(Athlete)
    if subject_ids:
        stmt = stmt.where(Athlete.id.in_(subject_ids))
    athletes = db.scalars(stmt).all()
    if not athletes:
        return []
    ids = [a.id for a in athletes]

    signal_map: dict[uuid.UUID, list[Signal]] = {}

    def add(entries: list[tuple[uuid.UUID, Signal]]) -> None:
        for subject_id, sig in entries:
            signal_map.setdefault(subject_id, []).append(sig)

    add(_event_signals(db, ids, TestingEvent, "TESTING", "test_date", type="test_type", classification="result_classification"))
    add(_event_signals(db, ids, BiologicalObservation, "BIOLOGICAL", "observation_date", marker="marker", unit="unit"))
    add(_event_signals(db, ids, WhereaboutsEvent, "WHEREABOUTS", "event_date", status="status"))
    add(_event_signals(db, ids, TravelEvent, "TRAVEL", "event_date", destination="destination"))
    add(_event_signals(db, ids, MedicalEvent, "MEDICAL", "event_date", classification="metadata_classification"))
    add(_event_signals(db, ids, SupplementEvent, "SUPPLEMENT", "event_date", note="usage_note"))
    add(_report_signals(db, ids))

    edges = _relationship_edges(db, ids)
    return [
        SubjectData(
            subject_id=a.id,
            subject_type="ATHLETE",
            signals=signal_map.get(a.id, []),
            relationships=edges.get(a.id, []),
        )
        for a in athletes
    ]