"""Domain read APIs for subjects: athletes and support personnel.

These endpoints expose the persisted subject records and their history (testing,
ABP/longitudinal observations, whereabouts, travel, events, intelligence and
relationships) for investigator review. They are read-only; they never assert a
violation -- they expose investigative context for human assessment.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.analytics import Alert
from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.investigations import Investigation
from app.models.intelligence import IntelligenceReport
from app.models.subjects import Athlete, SupportPerson
from app.security.rbac import Permissions
from app.services.domain_reads import (
    athlete_relationships,
    name_for,
    resolve_names,
)

router = APIRouter(tags=["subjects"])

_READ = [Depends(require_permissions(Permissions.ATHLETES_READ))]


def _paginate(limit: int, offset: int) -> tuple[int, int]:
    return min(max(limit, 1), 200), max(offset, 0)


def _athlete_summary(a: Athlete) -> dict:
    return {
        "id": str(a.id),
        "external_ref": a.external_ref,
        "full_name": a.full_name,
        "first_name": a.first_name,
        "last_name": a.last_name,
        "date_of_birth": a.date_of_birth.isoformat() if a.date_of_birth else None,
        "nationality": a.nationality,
        "sport": a.sport,
        "discipline": a.discipline,
        "gender": a.gender,
        "status": a.status,
        "team": {"id": str(a.team.id), "name": a.team.name} if a.team else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _support_summary(s: SupportPerson) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "external_ref": s.external_ref,
        "support_role": s.support_role,
        "organization": s.organization,
        "organization_id": str(s.organization_id) if s.organization_id else None,
        "country": s.country,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# --- Athletes ---------------------------------------------------------------


@router.get("/athletes", dependencies=_READ, summary="List/search athletes")
def list_athletes(
    q: Annotated[str | None, Query(description="Search first/last name or external reference")] = None,
    sport: Annotated[str | None, Query()] = None,
    nationality: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    limit, offset = _paginate(limit, offset)
    stmt = select(Athlete)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Athlete.first_name.ilike(like),
                Athlete.last_name.ilike(like),
                Athlete.external_ref.ilike(like),
            )
        )
    if sport:
        stmt = stmt.where(Athlete.sport == sport)
    if nationality:
        stmt = stmt.where(Athlete.nationality == nationality)
    if status_filter:
        stmt = stmt.where(Athlete.status == status_filter.upper())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Athlete.last_name, Athlete.first_name).offset(offset).limit(limit)
    ).all()
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "athletes": [_athlete_summary(a) for a in rows],
    }


def _get_athlete(db: Session, athlete_id: uuid.UUID) -> Athlete:
    athlete = db.get(Athlete, athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete


@router.get("/athletes/{athlete_id}", dependencies=_READ, summary="Athlete profile and context counts")
def athlete_detail(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    athlete = _get_athlete(db, athlete_id)

    def _count(model, **filters) -> int:
        stmt = select(func.count()).select_from(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        return db.scalar(stmt) or 0

    relationships = athlete_relationships(db, athlete_id)
    return {
        **_athlete_summary(athlete),
        "counts": {
            "testing_events": _count(TestingEvent, athlete_id=athlete_id),
            "biological_observations": _count(BiologicalObservation, athlete_id=athlete_id),
            "whereabouts_events": _count(WhereaboutsEvent, athlete_id=athlete_id),
            "travel_events": _count(TravelEvent, athlete_id=athlete_id),
            "medical_events": _count(MedicalEvent, athlete_id=athlete_id),
            "supplement_events": _count(SupplementEvent, athlete_id=athlete_id),
            "intelligence_reports": _count(
                IntelligenceReport, subject_type="ATHLETE", subject_id=athlete_id
            ),
            "alerts": _count(Alert, subject_type="ATHLETE", subject_id=athlete_id),
            "investigations": _count(Investigation, subject_type="ATHLETE", subject_id=athlete_id),
            "relationships": len(relationships),
        },
    }


def _tests(athlete_id: uuid.UUID, db: Session) -> list[TestingEvent]:
    return db.scalars(
        select(TestingEvent)
        .where(TestingEvent.athlete_id == athlete_id)
        .order_by(TestingEvent.test_date.desc())
    ).all()


@router.get("/athletes/{athlete_id}/tests", dependencies=_READ, summary="Testing history")
def athlete_tests(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_athlete(db, athlete_id)
    rows = _tests(athlete_id, db)
    return {
        "count": len(rows),
        "tests": [
            {
                "id": str(t.id),
                "test_date": t.test_date.isoformat(),
                "test_type": t.test_type,
                "location": t.location,
                "result_classification": t.result_classification,
                "laboratory_ref": t.laboratory_ref,
            }
            for t in rows
        ],
    }


@router.get("/athletes/{athlete_id}/abp", dependencies=_READ, summary="ABP / longitudinal biological observations")
def athlete_abp(
    athlete_id: uuid.UUID,
    marker: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_athlete(db, athlete_id)
    stmt = select(BiologicalObservation).where(
        BiologicalObservation.athlete_id == athlete_id
    )
    if marker:
        stmt = stmt.where(BiologicalObservation.marker == marker.upper())
    rows = db.scalars(
        stmt.order_by(BiologicalObservation.observation_date.desc())
    ).all()
    return {
        "count": len(rows),
        "observations": [
            {
                "id": str(o.id),
                "observation_date": o.observation_date.isoformat(),
                "marker": o.marker,
                "value": o.value,
                "unit": o.unit,
                "baseline_deviation": o.baseline_deviation,
            }
            for o in rows
        ],
    }


@router.get("/athletes/{athlete_id}/whereabouts", dependencies=_READ, summary="Whereabouts history")
def athlete_whereabouts(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_athlete(db, athlete_id)
    rows = db.scalars(
        select(WhereaboutsEvent)
        .where(WhereaboutsEvent.athlete_id == athlete_id)
        .order_by(WhereaboutsEvent.event_date.desc())
    ).all()
    return {
        "count": len(rows),
        "whereabouts": [
            {
                "id": str(w.id),
                "event_date": w.event_date.isoformat(),
                "event_type": w.event_type,
                "expected_location": w.expected_location,
                "observed_location": w.observed_location,
                "status": w.status,
            }
            for w in rows
        ],
    }


@router.get("/athletes/{athlete_id}/travel", dependencies=_READ, summary="Travel history")
def athlete_travel(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_athlete(db, athlete_id)
    rows = db.scalars(
        select(TravelEvent)
        .where(TravelEvent.athlete_id == athlete_id)
        .order_by(TravelEvent.event_date.desc())
    ).all()
    return {
        "count": len(rows),
        "travel": [
            {
                "id": str(t.id),
                "event_date": t.event_date.isoformat(),
                "origin": t.origin,
                "destination": t.destination,
                "event_type": t.event_type,
            }
            for t in rows
        ],
    }


@router.get("/athletes/{athlete_id}/events", dependencies=_READ, summary="Combined athlete timeline")
def athlete_timeline(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_athlete(db, athlete_id)
    entries: list[dict] = []

    for t in _tests(athlete_id, db):
        entries.append(
            {
                "date": t.test_date.isoformat(),
                "kind": "TESTING",
                "label": f"Testing{(' - ' + t.test_type) if t.test_type else ''}",
                "id": str(t.id),
            }
        )
    for o in db.scalars(
        select(BiologicalObservation).where(BiologicalObservation.athlete_id == athlete_id)
    ).all():
        entries.append(
            {
                "date": o.observation_date.isoformat(),
                "kind": "ABP",
                "label": f"Biological marker {o.marker}",
                "id": str(o.id),
            }
        )
    for w in db.scalars(
        select(WhereaboutsEvent).where(WhereaboutsEvent.athlete_id == athlete_id)
    ).all():
        entries.append(
            {
                "date": w.event_date.isoformat(),
                "kind": "WHEREABOUTS",
                "label": f"Whereabouts {w.event_type or 'entry'}",
                "id": str(w.id),
            }
        )
    for t in db.scalars(
        select(TravelEvent).where(TravelEvent.athlete_id == athlete_id)
    ).all():
        entries.append(
            {
                "date": t.event_date.isoformat(),
                "kind": "TRAVEL",
                "label": f"Travel {t.origin or '?'} -> {t.destination or '?'}",
                "id": str(t.id),
            }
        )
    for m in db.scalars(
        select(MedicalEvent).where(MedicalEvent.athlete_id == athlete_id)
    ).all():
        if m.event_date:
            entries.append(
                {
                    "date": m.event_date.isoformat(),
                    "kind": "MEDICAL",
                    "label": f"Medical {m.event_type or 'entry'}",
                    "id": str(m.id),
                }
            )
    for s in db.scalars(
        select(SupplementEvent).where(SupplementEvent.athlete_id == athlete_id)
    ).all():
        if s.event_date:
            entries.append(
                {
                    "date": s.event_date.isoformat(),
                    "kind": "SUPPLEMENT",
                    "label": "Supplement usage",
                    "id": str(s.id),
                }
            )
    for r in db.scalars(
        select(IntelligenceReport).where(
            IntelligenceReport.subject_type == "ATHLETE",
            IntelligenceReport.subject_id == athlete_id,
        )
    ).all():
        if r.report_date:
            entries.append(
                {
                    "date": r.report_date.isoformat(),
                    "kind": "INTELLIGENCE",
                    "label": f"Intelligence: {r.title}",
                    "id": str(r.id),
                }
            )
    entries.sort(key=lambda e: e["date"], reverse=True)
    return {"count": len(entries), "timeline": entries}


@router.get("/athletes/{athlete_id}/intelligence", dependencies=_READ, summary="Intelligence linked to athlete")
def athlete_intelligence(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_athlete(db, athlete_id)
    rows = db.scalars(
        select(IntelligenceReport)
        .where(
            IntelligenceReport.subject_type == "ATHLETE",
            IntelligenceReport.subject_id == athlete_id,
        )
        .order_by(IntelligenceReport.ingestion_date.desc())
    ).all()
    return {
        "count": len(rows),
        "reports": [
            {
                "id": str(r.id),
                "title": r.title,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "ingestion_date": r.ingestion_date.isoformat() if r.ingestion_date else None,
                "status": r.status,
                "info_category": r.info_category,
                "reliability": r.reliability,
                "confidentiality": r.confidentiality,
            }
            for r in rows
        ],
    }


def _relationship_rows(db: Session, entity_type: str, entity_id: uuid.UUID) -> list:
    from app.models.relationships import EntityRelationship

    stmt = select(EntityRelationship).where(
        (EntityRelationship.from_entity_type == entity_type)
        & (EntityRelationship.from_entity_id == entity_id)
        | (EntityRelationship.to_entity_type == entity_type)
        & (EntityRelationship.to_entity_id == entity_id)
    )
    return list(db.scalars(stmt.order_by(EntityRelationship.created_at.desc())).all())


def _serialize_relationships(db: Session, rows: list) -> list[dict]:
    pairs: list[tuple[str, uuid.UUID]] = []
    for r in rows:
        pairs.append((r.from_entity_type, r.from_entity_id))
        pairs.append((r.to_entity_type, r.to_entity_id))
    names = resolve_names(db, pairs)
    items = []
    for r in rows:
        items.append(
            {
                "id": str(r.id),
                "relationship_type": r.rel_type.name if r.rel_type else None,
                "from_entity_type": r.from_entity_type,
                "from_entity_id": str(r.from_entity_id),
                "from_name": names.get((r.from_entity_type, str(r.from_entity_id))),
                "to_entity_type": r.to_entity_type,
                "to_entity_id": str(r.to_entity_id),
                "to_name": names.get((r.to_entity_type, str(r.to_entity_id))),
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "confidence": r.confidence,
                "status": "INACTIVE" if r.end_date else "ACTIVE",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return items


@router.get("/athletes/{athlete_id}/relationships", dependencies=_READ, summary="Relationships involving athlete")
def athlete_relationships_endpoint(athlete_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_athlete(db, athlete_id)
    rows = _relationship_rows(db, "ATHLETE", athlete_id)
    return {"count": len(rows), "relationships": _serialize_relationships(db, rows)}


# --- Support personnel ------------------------------------------------------


@router.get("/support-persons", dependencies=_READ, summary="List/search support personnel")
def list_support_persons(
    q: Annotated[str | None, Query()] = None,
    support_role: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    limit, offset = _paginate(limit, offset)
    stmt = select(SupportPerson)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(SupportPerson.name.ilike(like), SupportPerson.external_ref.ilike(like)))
    if support_role:
        stmt = stmt.where(SupportPerson.support_role == support_role)
    if status_filter:
        stmt = stmt.where(SupportPerson.status == status_filter.upper())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(SupportPerson.name).offset(offset).limit(limit)).all()
    return {"count": total, "limit": limit, "offset": offset, "support_persons": [_support_summary(s) for s in rows]}


def _get_support_person(db: Session, person_id: uuid.UUID) -> SupportPerson:
    person = db.get(SupportPerson, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Support person not found")
    return person


@router.get("/support-persons/{person_id}", dependencies=_READ, summary="Support person profile")
def support_person_detail(person_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    person = _get_support_person(db, person_id)
    relationships = _relationship_rows(db, "SUPPORT_PERSON", person_id)
    intel = db.scalars(
        select(IntelligenceReport).where(
            IntelligenceReport.subject_type == "SUPPORT_PERSON",
            IntelligenceReport.subject_id == person_id,
        )
    ).all()
    return {
        **_support_summary(person),
        "counts": {
            "relationships": len(relationships),
            "intelligence_reports": len(intel),
        },
    }


@router.get("/support-persons/{person_id}/relationships", dependencies=_READ, summary="Relationships involving support person")
def support_person_relationships(person_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_support_person(db, person_id)
    rows = _relationship_rows(db, "SUPPORT_PERSON", person_id)
    return {"count": len(rows), "relationships": _serialize_relationships(db, rows)}


@router.get("/support-persons/{person_id}/intelligence", dependencies=_READ, summary="Intelligence linked to support person")
def support_person_intelligence(person_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_support_person(db, person_id)
    rows = db.scalars(
        select(IntelligenceReport)
        .where(
            IntelligenceReport.subject_type == "SUPPORT_PERSON",
            IntelligenceReport.subject_id == person_id,
        )
        .order_by(IntelligenceReport.ingestion_date.desc())
    ).all()
    return {
        "count": len(rows),
        "reports": [
            {
                "id": str(r.id),
                "title": r.title,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "ingestion_date": r.ingestion_date.isoformat() if r.ingestion_date else None,
                "status": r.status,
                "info_category": r.info_category,
                "reliability": r.reliability,
                "confidentiality": r.confidentiality,
            }
            for r in rows
        ],
    }