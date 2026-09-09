"""Shared read-model helpers for the domain read APIs (G3).

Provides polymorphic entity-name resolution across the subject/intelligence link
models and the dashboard summary aggregation. Keeping the meaningful queries and
serialization here keeps route handlers thin while preserving the existing
modular-monolith style (API route -> service -> domain models -> database).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis.serializers import alert_summary, run_summary
from app.models.analytics import Alert, AnalysisRun
from app.models.intelligence import IntelligenceReport, IntelligenceSource
from app.models.investigations import Investigation
from app.models.relationships import EntityRelationship
from app.models.subjects import (
    Athlete,
    Organization,
    Provider,
    Supplement,
    SupportPerson,
    Team,
)

# Subject type -> model for polymorphic subject links (intelligence + relationships).
ENTITY_MODELS: dict[str, type] = {
    "ATHLETE": Athlete,
    "SUPPORT_PERSON": SupportPerson,
    "TEAM": Team,
    "ORGANIZATION": Organization,
    "PROVIDER": Provider,
    "SUPPLEMENT": Supplement,
}


def _display_name(entity_type: str, row) -> str:
    if entity_type == "ATHLETE":
        return row.full_name
    return (
        getattr(row, "name", None)
        or getattr(row, "external_ref", None)
        or str(row.id)[:8]
    )


def resolve_names(
    db: Session, pairs: list[tuple[str, uuid.UUID]]
) -> dict[tuple[str, str], str]:
    """Resolve a batch of (entity_type, entity_id) pairs to display names.

    Batches by entity type to avoid one query per resolved row.
    """
    resolved: dict[tuple[str, str], str] = {}
    by_type: dict[str, set[uuid.UUID]] = {}
    for entity_type, entity_id in pairs:
        by_type.setdefault(entity_type, set()).add(entity_id)
    for entity_type, ids in by_type.items():
        model = ENTITY_MODELS.get(entity_type)
        if model is None:
            continue
        rows = db.scalars(select(model).where(model.id.in_(ids))).all()
        for row in rows:
            resolved[(entity_type, str(row.id))] = _display_name(entity_type, row)
    return resolved


def name_for(db: Session, entity_type: str, entity_id: uuid.UUID) -> str | None:
    return resolve_names(db, [(entity_type, entity_id)]).get((entity_type, str(entity_id)))


def _investigation_summary(inv: Investigation, name: str | None) -> dict:
    return {
        "id": str(inv.id),
        "case_ref": inv.case_ref,
        "title": inv.title,
        "status": inv.status,
        "priority": inv.priority,
        "subject_type": inv.subject_type,
        "subject_id": str(inv.subject_id),
        "subject_name": name,
        "assigned_to": str(inv.assigned_to) if inv.assigned_to else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def dashboard_summary(
    db: Session,
    alert_limit: int = 5,
    intel_limit: int = 5,
    run_limit: int = 5,
    investigation_limit: int = 5,
) -> dict:
    """Computed read-only dashboard summary over actual persisted data.

    No fabricated metrics: every figure is an aggregate/count from the database or
    a snapshot of real rows.
    """
    alert_total = db.scalar(select(func.count(Alert.id))) or 0
    alert_by_status = dict(
        db.execute(select(Alert.status, func.count()).group_by(Alert.status)).all()
    )
    alert_by_priority = dict(
        db.execute(
            select(Alert.priority_level, func.count()).group_by(Alert.priority_level)
        ).all()
    )
    recent_alerts = db.scalars(
        select(Alert).order_by(Alert.created_at.desc()).limit(alert_limit)
    ).all()

    inv_total = db.scalar(select(func.count(Investigation.id))) or 0
    inv_by_status = dict(
        db.execute(
            select(Investigation.status, func.count()).group_by(Investigation.status)
        ).all()
    )
    inv_open = int(inv_by_status.get("OPEN", 0))
    recent_inv = db.scalars(
        select(Investigation).order_by(Investigation.created_at.desc()).limit(investigation_limit)
    ).all()

    intel_total = db.scalar(select(func.count(IntelligenceReport.id))) or 0
    intel_new = (
        db.scalar(
            select(func.count(IntelligenceReport.id)).where(
                IntelligenceReport.status == "NEW"
            )
        )
        or 0
    )
    recent_intel = db.scalars(
        select(IntelligenceReport)
        .order_by(IntelligenceReport.ingestion_date.desc())
        .limit(intel_limit)
    ).all()

    run_total = db.scalar(select(func.count(AnalysisRun.id))) or 0
    recent_runs = db.scalars(
        select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(run_limit)
    ).all()

    athletes_total = db.scalar(select(func.count(Athlete.id))) or 0
    sources_total = db.scalar(select(func.count(IntelligenceSource.id))) or 0

    pairs: list[tuple[str, uuid.UUID]] = []
    pairs.extend((a.subject_type, a.subject_id) for a in recent_alerts)
    pairs.extend((i.subject_type, i.subject_id) for i in recent_inv)
    pairs.extend((r.subject_type, r.subject_id) for r in recent_intel)
    names = resolve_names(db, pairs)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alerts": {
            "total": alert_total,
            "by_status": alert_by_status,
            "priority_distribution": alert_by_priority,
            "recent": [alert_summary(a) for a in recent_alerts],
        },
        "investigations": {
            "total": inv_total,
            "open": inv_open,
            "by_status": inv_by_status,
            "recent": [
                _investigation_summary(
                    inv, names.get((inv.subject_type, str(inv.subject_id)))
                )
                for inv in recent_inv
            ],
        },
        "intelligence": {
            "reports_total": intel_total,
            "new_reports": intel_new,
            "recent": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "report_date": r.report_date.isoformat() if r.report_date else None,
                    "ingestion_date": r.ingestion_date.isoformat() if r.ingestion_date else None,
                    "status": r.status,
                    "info_category": r.info_category,
                    "subject_type": r.subject_type,
                    "subject_id": str(r.subject_id) if r.subject_id else None,
                    "subject_name": names.get((r.subject_type or "", str(r.subject_id)))
                    if r.subject_id
                    else None,
                }
                for r in recent_intel
            ],
        },
        "analysis": {
            "runs_total": run_total,
            "recent": [run_summary(r) for r in recent_runs],
        },
        "entities": {
            "athletes_total": athletes_total,
            "intelligence_sources_total": sources_total,
        },
    }


def athlete_relationships(db: Session, athlete_id: uuid.UUID) -> list[EntityRelationship]:
    """All entity relationships involving an athlete on either side."""
    return db.scalars(
        select(EntityRelationship)
        .where(
            (EntityRelationship.from_entity_type == "ATHLETE")
            & (EntityRelationship.from_entity_id == athlete_id)
            | (EntityRelationship.to_entity_type == "ATHLETE")
            & (EntityRelationship.to_entity_id == athlete_id)
        )
        .order_by(EntityRelationship.created_at.desc())
    ).all()