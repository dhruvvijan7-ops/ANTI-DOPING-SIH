"""Investigation workspace API (STAGE F/G).

Everything returned here is investigative *work product* owned by humans. Analytical
data is preserved by reference (via the originating alert) and never duplicated.
The relationship graph is descriptive: association does not imply wrongdoing.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permissions
from app.analysis import serializers as analysis_serializers
from app.db.session import get_db
from app.investigations import serializers
from app.models.analytics import Alert, CorrelationResult
from app.models.audit import AuditEvent
from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.identity import User
from app.models.intelligence import IntelligenceReport
from app.models.investigations import (
    PRIORITY_LEVELS,
    INVESTIGATION_STATUSES,
    TASK_STATUSES,
    EvidenceItem,
    Finding,
    Investigation,
    InvestigationNote,
    InvestigationTask,
)
from app.models.relationships import EntityRelationship
from app.models.subjects import Athlete, Organization, Provider, Supplement, SupportPerson, Team
from app.security.rbac import Permissions
from app.services.audit_service import record_audit

router = APIRouter(tags=["investigations"])


class InvestigationCreateBody(BaseModel):
    title: str
    description: str | None = None
    priority: str = "MODERATE"
    subject_type: str = "ATHLETE"
    subject_id: uuid.UUID
    originating_alert_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None


class InvestigationPatchBody(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None


class EvidenceBody(BaseModel):
    title: str
    description: str | None = None
    evidence_type: str = "DOCUMENT"
    source: str | None = None
    classification: str = "UNCLASSIFIED"
    item_date: datetime | None = None
    relationship_to_case: str | None = None


class TaskBody(BaseModel):
    title: str
    description: str | None = None
    assigned_to: uuid.UUID | None = None
    status: str = "OPEN"
    due_date: str | None = None


class TaskPatchBody(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: uuid.UUID | None = None
    status: str | None = None
    due_date: str | None = None


class NoteBody(BaseModel):
    content: str


class FindingBody(BaseModel):
    title: str
    statement: str
    supporting_evidence: str | None = None
    assessment: str | None = None
    confident: bool = False


class FindingPatchBody(BaseModel):
    title: str | None = None
    statement: str | None = None
    supporting_evidence: str | None = None
    assessment: str | None = None
    confident: bool | None = None


def _get_inv(db: Session, investigation_id: uuid.UUID) -> Investigation:
    inv = db.get(Investigation, investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


def _validate_priority(db: Session, value: str) -> str:
    value = value.upper()
    if value not in PRIORITY_LEVELS:
        raise HTTPException(status_code=422, detail="Unsupported priority level")
    return value


def _validate_status(db: Session, value: str, allowed: tuple[str, ...]) -> str:
    value = value.upper()
    if value not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported status")
    return value


# --------------------------------------------------------------------------- case
@router.get("/investigations", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def list_investigations(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Investigation).order_by(Investigation.created_at.desc())
    if status_filter:
        stmt = stmt.where(Investigation.status == status_filter.upper())
    if subject_id:
        stmt = stmt.where(Investigation.subject_id == subject_id)
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "investigations": [serializers.investigation_summary(i) for i in rows]}


@router.post("/investigations", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_CREATE))])
def create_investigation(
    body: InvestigationCreateBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = Investigation(
        title=body.title[:255],
        description=body.description,
        status="OPEN",
        priority=_validate_priority(db, body.priority),
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        originating_alert_id=body.originating_alert_id,
        assigned_to=body.assigned_to,
        created_by=user.id,
    )
    if body.originating_alert_id is not None:
        alert = db.get(Alert, body.originating_alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Originating alert not found")
        alert.status = "CONVERTED"
        alert.investigation_id = None  # fixed below after flush
        alert.triage_meta_json = {"action": "ALERT_CONVERTED", "note": None, "by": str(user.id)}
    db.add(inv)
    db.flush()
    if body.originating_alert_id is not None:
        alert.investigation_id = inv.id
    record_audit(
        db,
        actor_id=user.id,
        action="INVESTIGATION_CREATED",
        entity_type="INVESTIGATION",
        entity_id=str(inv.id),
        metadata={
            "case_ref": inv.case_ref,
            "subject_id": str(inv.subject_id),
            "priority": inv.priority,
            "originating_alert_id": str(inv.originating_alert_id) if inv.originating_alert_id else None,
        },
    )
    db.commit()
    return serializers.investigation_summary(inv)


@router.patch("/investigations/{investigation_id}", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def update_investigation(
    investigation_id: uuid.UUID,
    body: InvestigationPatchBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    if body.title is not None:
        inv.title = body.title[:255]
    if body.description is not None:
        inv.description = body.description
    if body.priority is not None:
        inv.priority = _validate_priority(db, body.priority)
    record_audit(
        db,
        actor_id=user.id,
        action="INVESTIGATION_UPDATED",
        entity_type="INVESTIGATION",
        entity_id=str(inv.id),
        metadata={"case_ref": inv.case_ref},
    )
    db.commit()
    return serializers.investigation_summary(inv)


@router.post("/investigations/{investigation_id}/close", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def close_investigation(
    investigation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    inv.status = "CLOSED"
    inv.closed_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor_id=user.id,
        action="INVESTIGATION_CLOSED",
        entity_type="INVESTIGATION",
        entity_id=str(inv.id),
        metadata={"case_ref": inv.case_ref},
    )
    db.commit()
    return serializers.investigation_summary(inv)


@router.get("/investigations/{investigation_id}", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def investigation_overview(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)
    subject_label = str(inv.subject_id)
    if inv.subject_type == "ATHLETE":
        athlete = db.get(Athlete, inv.subject_id)
        if athlete is not None:
            subject_label = f"{athlete.first_name or ''} {athlete.last_name or ''}".strip() or athlete.external_ref or str(inv.subject_id)
    origin = None
    if inv.originating_alert_id:
        alert = db.get(Alert, inv.originating_alert_id)
        if alert is not None:
            origin = {
                "alert_id": str(alert.id),
                "alert_ref": alert.alert_ref,
                "priority_level": alert.priority_level,
                "score": alert.score,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }
    return {
        "investigation": serializers.investigation_summary(inv),
        "subject_label": subject_label,
        "originating_alert": origin,
        "counts": {
            "alerts": len(inv.alerts),
            "evidence": len(inv.evidence),
            "tasks": len(inv.tasks),
            "notes": len(inv.notes),
            "findings": len(inv.findings),
            "reports": len(inv.reports),
        },
    }


# ------------------------------------------------------------------- intelligence
@router.get("/investigations/{investigation_id}/intelligence", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def investigation_intelligence(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)
    rows = db.scalars(
        select(IntelligenceReport).where(
            IntelligenceReport.subject_type == inv.subject_type,
            IntelligenceReport.subject_id == inv.subject_id,
        ).order_by(IntelligenceReport.report_date.desc())
    ).all()
    items = []
    for r in rows:
        items.append({
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "reliability": r.reliability,
            "info_category": r.info_category,
            "status": r.status,
            "source": r.source.name if r.source else None,
            "source_type": r.source.source_type if r.source else None,
            "is_duplicate": r.is_duplicate,
        })
    return {"count": len(items), "intelligence": items}


# ----------------------------------------------------------------------- timeline
@router.get("/investigations/{investigation_id}/timeline", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def investigation_timeline(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)

    # Signal relevance: event/report ids referenced by the originating run's
    # temporal/cross-source correlations are investigative leads, not raw context.
    signal_ids: set[str] = set()
    if inv.originating_alert_id:
        alert = db.get(Alert, inv.originating_alert_id)
        if alert is not None:
            for corr in db.scalars(
                select(CorrelationResult).where(
                    CorrelationResult.analysis_run_id == alert.analysis_run_id,
                    CorrelationResult.subject_id == alert.subject_id,
                    CorrelationResult.correlation_type.in_(["TEMPORAL", "CROSS_SOURCE"]),
                )
            ).all():
                signal_ids.update(corr.signal_ids_json or [])

    def relevant(record_id: uuid.UUID) -> str:
        return "ALERT_SIGNAL" if str(record_id) in signal_ids else "CONTEXT"

    entries = []

    def add_events(model, name: str) -> None:
        for row in db.scalars(select(model).where(model.athlete_id == inv.subject_id)).all():
            occurred = getattr(row, "test_date", None) or getattr(row, "observation_date", None) or getattr(row, "event_date", None)
            if occurred is None:
                continue
            entries.append({
                "event_type": name,
                "occurred_at": occurred.isoformat(),
                "source": getattr(getattr(row, "source", None), "name", None) or "UNKNOWN",
                "related_entity": str(inv.subject_id),
                "relevance": relevant(row.id),
                "record_id": str(row.id),
                "origin": model.__tablename__,
                "summary": str(getattr(row, "result_classification", None) or getattr(row, "status", None) or getattr(row, "marker", None) or getattr(row, "event_type", None) or getattr(row, "destination", None) or ""),
            })

    add_events(TestingEvent, "TESTING")
    add_events(BiologicalObservation, "BIOLOGICAL")
    add_events(WhereaboutsEvent, "WHEREABOUTS")
    add_events(TravelEvent, "TRAVEL")
    add_events(MedicalEvent, "MEDICAL")
    add_events(SupplementEvent, "SUPPLEMENT")

    for r in db.scalars(
        select(IntelligenceReport).where(
            IntelligenceReport.subject_type == inv.subject_type,
            IntelligenceReport.subject_id == inv.subject_id,
        )
    ).all():
        entries.append({
            "event_type": "INTELLIGENCE_REPORT",
            "occurred_at": (r.report_date or r.ingestion_date.date()).isoformat(),
            "source": r.source.name if r.source else None,
            "related_entity": str(inv.subject_id),
            "relevance": relevant(r.id),
            "record_id": str(r.id),
            "origin": "intelligence_reports",
            "summary": r.title,
        })

    for e in inv.evidence:
        entries.append({
            "event_type": "EVIDENCE",
            "occurred_at": (e.item_date or e.created_at).isoformat() if (e.item_date or e.created_at) else None,
            "source": e.source or "CASE WORK",
            "related_entity": str(inv.subject_id),
            "relevance": "CONTEXT",
            "record_id": str(e.id),
            "origin": "evidence_items",
            "summary": e.title,
        })

    for n in inv.notes:
        entries.append({
            "event_type": "NOTE",
            "occurred_at": n.created_at.isoformat() if n.created_at else None,
            "source": "CASE WORK",
            "related_entity": str(inv.subject_id),
            "relevance": "CONTEXT",
            "record_id": str(n.id),
            "origin": "investigation_notes",
            "summary": n.content,
        })

    for alert in inv.alerts:
        entries.append({
            "event_type": "ALERT",
            "occurred_at": alert.created_at.isoformat() if alert.created_at else None,
            "source": "ANALYSIS ENGINE",
            "related_entity": str(inv.subject_id),
            "relevance": "ALERT_SIGNAL",
            "record_id": str(alert.id),
            "origin": "alerts",
            "summary": alert.title,
        })

    entries.sort(key=lambda e: e["occurred_at"] or "")
    return {"count": len(entries), "timeline": entries}


# ----------------------------------------------------------------------- evidence
@router.get("/investigations/{investigation_id}/evidence", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def list_evidence(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)
    rows = sorted(inv.evidence, key=lambda e: e.created_at or datetime.min, reverse=True)
    return {"count": len(rows), "evidence": [serializers.evidence_item(e) for e in rows]}


@router.post("/investigations/{investigation_id}/evidence", dependencies=[Depends(require_permissions(Permissions.EVIDENCE_CREATE))])
def create_evidence(
    investigation_id: uuid.UUID,
    body: EvidenceBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    item = EvidenceItem(
        investigation_id=inv.id,
        title=body.title,
        description=body.description,
        evidence_type=body.evidence_type,
        source=body.source,
        classification=body.classification or "UNCLASSIFIED",
        item_date=body.item_date,
        relationship_to_case=body.relationship_to_case,
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="EVIDENCE_CREATED",
        entity_type="EVIDENCE",
        entity_id=str(item.id),
        metadata={"investigation_id": str(inv.id), "title": item.title, "classification": item.classification},
    )
    db.commit()
    return serializers.evidence_item(item)


@router.patch("/investigations/{investigation_id}/evidence/{evidence_id}", dependencies=[Depends(require_permissions(Permissions.EVIDENCE_MODIFY))])
def update_evidence(
    investigation_id: uuid.UUID,
    evidence_id: uuid.UUID,
    body: EvidenceBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    item = db.get(EvidenceItem, evidence_id)
    if item is None or item.investigation_id != inv.id:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    for field in ("title", "description", "evidence_type", "source", "classification", "item_date", "relationship_to_case"):
        value = getattr(body, field)
        if value is not None:
            setattr(item, field, value)
    record_audit(
        db,
        actor_id=user.id,
        action="EVIDENCE_UPDATED",
        entity_type="EVIDENCE",
        entity_id=str(item.id),
        metadata={"investigation_id": str(inv.id), "title": item.title},
    )
    db.commit()
    return serializers.evidence_item(item)


# -------------------------------------------------------------------------- tasks
@router.get("/investigations/{investigation_id}/tasks", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def list_tasks(
    investigation_id: uuid.UUID,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: Session = Depends(get_db),
) -> dict:
    inv = _get_inv(db, investigation_id)
    rows = [t for t in inv.tasks if not status_filter or t.status == status_filter.upper()]
    rows.sort(key=lambda t: t.created_at or datetime.min, reverse=True)
    return {"count": len(rows), "tasks": [serializers.task_row(t) for t in rows]}


@router.post("/investigations/{investigation_id}/tasks", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def create_task(
    investigation_id: uuid.UUID,
    body: TaskBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    task = InvestigationTask(
        investigation_id=inv.id,
        title=body.title,
        description=body.description,
        assigned_to=body.assigned_to,
        status=_validate_status(db, body.status, TASK_STATUSES),
        due_date=None if not body.due_date else datetime.fromisoformat(body.due_date).date(),
        created_by=user.id,
    )
    db.add(task)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="TASK_CREATED",
        entity_type="TASK",
        entity_id=str(task.id),
        metadata={"investigation_id": str(inv.id), "title": task.title, "status": task.status},
    )
    db.commit()
    return serializers.task_row(task)


@router.patch("/investigations/{investigation_id}/tasks/{task_id}", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def update_task(
    investigation_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskPatchBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    task = db.get(InvestigationTask, task_id)
    if task is None or task.investigation_id != inv.id:
        raise HTTPException(status_code=404, detail="Task not found")
    changed = []
    if body.title is not None:
        task.title = body.title
        changed.append("title")
    if body.description is not None:
        task.description = body.description
        changed.append("description")
    if body.assigned_to is not None:
        task.assigned_to = body.assigned_to
        changed.append("assigned_to")
    if body.status is not None:
        task.status = _validate_status(db, body.status, TASK_STATUSES)
        changed.append("status")
    if body.due_date is not None:
        task.due_date = datetime.fromisoformat(body.due_date).date()
        changed.append("due_date")
    record_audit(
        db,
        actor_id=user.id,
        action="TASK_UPDATED",
        entity_type="TASK",
        entity_id=str(task.id),
        metadata={"investigation_id": str(inv.id), "title": task.title, "changed": changed, "status": task.status},
    )
    db.commit()
    return serializers.task_row(task)


# -------------------------------------------------------------------------- notes
@router.get("/investigations/{investigation_id}/notes", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def list_notes(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)
    rows = sorted(inv.notes, key=lambda n: n.created_at or datetime.min, reverse=True)
    return {"count": len(rows), "notes": [serializers.note_row(n) for n in rows]}


@router.post("/investigations/{investigation_id}/notes", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def create_note(
    investigation_id: uuid.UUID,
    body: NoteBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    note = InvestigationNote(investigation_id=inv.id, author_id=user.id, content=body.content)
    db.add(note)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="NOTE_CREATED",
        entity_type="NOTE",
        entity_id=str(note.id),
        metadata={"investigation_id": str(inv.id)},
    )
    db.commit()
    return serializers.note_row(note)


@router.patch("/investigations/{investigation_id}/notes/{note_id}", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def update_note(
    investigation_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    note = db.get(InvestigationNote, note_id)
    if note is None or note.investigation_id != inv.id:
        raise HTTPException(status_code=404, detail="Note not found")
    note.content = body.content
    record_audit(
        db,
        actor_id=user.id,
        action="NOTE_UPDATED",
        entity_type="NOTE",
        entity_id=str(note.id),
        metadata={"investigation_id": str(inv.id)},
    )
    db.commit()
    return serializers.note_row(note)


# ------------------------------------------------------------------------ findings
@router.get("/investigations/{investigation_id}/findings", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def list_findings(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)
    rows = sorted(inv.findings, key=lambda f: f.created_at or datetime.min, reverse=True)
    return {"count": len(rows), "findings": [serializers.finding_row(f) for f in rows]}


@router.post("/investigations/{investigation_id}/findings", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def create_finding(
    investigation_id: uuid.UUID,
    body: FindingBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    finding = Finding(
        investigation_id=inv.id,
        title=body.title,
        statement=body.statement,
        supporting_evidence=body.supporting_evidence,
        assessment=body.assessment,
        confident=body.confident,
        author_id=user.id,
    )
    db.add(finding)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="FINDING_CREATED",
        entity_type="FINDING",
        entity_id=str(finding.id),
        metadata={"investigation_id": str(inv.id), "title": finding.title, "confident": finding.confident},
    )
    db.commit()
    return serializers.finding_row(finding)


@router.patch("/investigations/{investigation_id}/findings/{finding_id}", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_MODIFY))])
def update_finding(
    investigation_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: FindingPatchBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _get_inv(db, investigation_id)
    finding = db.get(Finding, finding_id)
    if finding is None or finding.investigation_id != inv.id:
        raise HTTPException(status_code=404, detail="Finding not found")
    for field in ("title", "statement", "supporting_evidence", "assessment", "confident"):
        value = getattr(body, field)
        if value is not None:
            setattr(finding, field, value)
    record_audit(
        db,
        actor_id=user.id,
        action="FINDING_UPDATED",
        entity_type="FINDING",
        entity_id=str(finding.id),
        metadata={"investigation_id": str(inv.id), "title": finding.title},
    )
    db.commit()
    return serializers.finding_row(finding)


# ------------------------------------------------------------------ relationship graph
_ENTITY_MODELS = {
    "ATHLETE": Athlete,
    "TEAM": Team,
    "ORGANIZATION": Organization,
    "PROVIDER": Provider,
    "SUPPORT_PERSON": SupportPerson,
    "SUPPLEMENT": Supplement,
}

def _label_for(db: Session, entity_type: str, entity_id: uuid.UUID) -> str:
    model = _ENTITY_MODELS.get(entity_type)
    if model is None:
        return str(entity_id)[:8]
    row = db.get(model, entity_id)
    if row is None:
        return str(entity_id)[:8]
    name = getattr(row, "name", None) or (
        f"{getattr(row, 'first_name', '') or ''} {getattr(row, 'last_name', '') or ''}".strip()
    )
    return name or (getattr(row, "external_ref", None) or str(entity_id)[:8])


@router.get("/investigations/{investigation_id}/relationships", dependencies=[Depends(require_permissions(Permissions.INVESTIGATIONS_READ))])
def relationship_graph(
    investigation_id: uuid.UUID,
    rel_types: Annotated[list[str] | None, Query(alias="rel_type")] = None,
    db: Session = Depends(get_db),
) -> dict:
    """Graph contract for the React Flow visualizer (STAGE F/G §10).

    Nodes: the case subject plus every directly-related entity from the relational
    store. Edges: the underlying relationship records (type, confidence, dates,
    source). The graph is descriptive only - association does not imply wrongdoing.
    """
    inv = _get_inv(db, investigation_id)
    rows = db.scalars(
        select(EntityRelationship).where(
            (EntityRelationship.from_entity_type == inv.subject_type)
            & (EntityRelationship.from_entity_id == inv.subject_id)
            | (EntityRelationship.to_entity_type == inv.subject_type)
            & (EntityRelationship.to_entity_id == inv.subject_id)
        )
    ).all()

    filter_types = {t.upper() for t in (rel_types or [])}
    nodes: dict[str, dict] = {}
    edges = []
    edges_seen: set[tuple[str, str, str]] = set()

    subject_key = f"{inv.subject_type}:{inv.subject_id}"
    nodes[subject_key] = {
        "id": subject_key,
        "label": _label_for(db, inv.subject_type, inv.subject_id),
        "kind": inv.subject_type,
        "is_subject": True,
    }

    for row in rows:
        rel_name = row.rel_type.name if row.rel_type else "UNKNOWN"
        if filter_types and rel_name not in filter_types:
            continue
        other_type, other_id = (
            (row.to_entity_type, row.to_entity_id)
            if row.from_entity_id == inv.subject_id
            else (row.from_entity_type, row.from_entity_id)
        )
        other_key = f"{other_type}:{other_id}"
        if other_key not in nodes:
            nodes[other_key] = {
                "id": other_key,
                "label": _label_for(db, other_type, other_id),
                "kind": other_type,
                "is_subject": False,
            }
        edge_key = (subject_key, other_key, rel_name)
        if edge_key in edges_seen:
            continue
        edges_seen.add(edge_key)
        edges.append({
            "id": f"e{len(edges) + 1}",
            "source": subject_key,
            "target": other_key,
            "label": rel_name,
            "data": {
                "relationship_type": rel_name,
                "confidence": row.confidence,
                "start_date": row.start_date.isoformat() if row.start_date else None,
                "end_date": row.end_date.isoformat() if row.end_date else None,
                "source": None,
                "relationship_id": str(row.id),
            },
        })

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
        "note": "Associations in this graph are descriptive and do not imply wrongdoing.",
    }


# ---------------------------------------------------------------------------- audit
@router.get("/investigations/{investigation_id}/audit", dependencies=[Depends(require_permissions(Permissions.AUDIT_READ))])
def investigation_audit(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _get_inv(db, investigation_id)

    child_ids = {
        "EVIDENCE": {str(e.id) for e in inv.evidence},
        "TASK": {str(t.id) for t in inv.tasks},
        "NOTE": {str(n.id) for n in inv.notes},
        "FINDING": {str(f.id) for f in inv.findings},
        "REPORT": {str(r.id) for r in inv.reports},
    }
    alert_ids = {str(a.id) for a in inv.alerts} | (
        {str(inv.originating_alert_id)} if inv.originating_alert_id else set()
    )

    events = db.scalars(select(AuditEvent)).all()
    filtered = []
    for event in events:
        matches = False
        if event.entity_type == "INVESTIGATION" and event.entity_id == str(inv.id):
            matches = True
        elif event.entity_type == "ALERT" and event.entity_id in alert_ids:
            matches = True
        elif event.entity_type in child_ids and event.entity_id in child_ids[event.entity_type]:
            matches = True
        if matches:
            filtered.append(event)
    filtered.sort(key=lambda e: e.timestamp or datetime.min, reverse=True)

    items = []
    for e in filtered:
        metadata = None
        if e.metadata_json:
            try:
                metadata = json.loads(e.metadata_json)
            except (ValueError, TypeError):
                metadata = e.metadata_json
        items.append({
            "id": str(e.id),
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "actor": f"{e.actor.full_name or e.actor.username}" if e.actor else None,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "metadata": metadata,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        })
    return {"count": len(items), "audit": items}