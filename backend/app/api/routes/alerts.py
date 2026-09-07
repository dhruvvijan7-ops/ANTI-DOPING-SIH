"""Alerts API: listing, detail and traceability back to analysis results."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import serializers
from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.analytics import (
    Alert,
    AlertSignal,
    AnomalyResult,
    CorrelationResult,
    FeatureSnapshot,
    NetworkResult,
    PriorityScore,
    RuleResult,
)
from app.models.identity import User
from app.models.investigations import PRIORITY_LEVELS, Investigation
from app.security.rbac import Permissions
from app.services.audit_service import record_audit

router = APIRouter(tags=["alerts"])

_SIGNAL_MODELS = {
    "RULE": RuleResult,
    "ANOMALY": AnomalyResult,
    "TEMPORAL": CorrelationResult,
    "CROSS_SOURCE": CorrelationResult,
    "NETWORK": NetworkResult,
}

# Triage destinations the generic status endpoint may set (kept for compatibility).
GENERIC_STATUSES = {"NEW", "REVIEWED", "ACTIONED", "DISMISSED"}


class AlertStatusBody(BaseModel):
    status: str


class TriageNoteBody(BaseModel):
    note: str | None = None


class ConvertBody(BaseModel):
    priority: str | None = None
    assigned_to: uuid.UUID | None = None
    title: str | None = None
    note: str | None = None


@router.get("/alerts", dependencies=[Depends(require_permissions(Permissions.ALERTS_READ))])
def list_alerts(
    run_id: Annotated[uuid.UUID | None, Query()] = None,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if run_id:
        stmt = stmt.where(Alert.analysis_run_id == run_id)
    if subject_id:
        stmt = stmt.where(Alert.subject_id == subject_id)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter.upper())
    alerts = db.scalars(stmt).all()
    return {"count": len(alerts), "alerts": [serializers.alert_summary(a) for a in alerts]}


@router.get("/alerts/{alert_id}", dependencies=[Depends(require_permissions(Permissions.ALERTS_READ))])
def alert_detail(alert_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    priority = db.get(PriorityScore, alert.priority_score_id)
    if priority is None:
        raise HTTPException(status_code=404, detail="Alert priority score missing")

    signals = db.scalars(
        select(AlertSignal).where(AlertSignal.alert_id == alert.id)
    ).all()

    serializer_map = {
        "RULE": serializers.rule_result,
        "ANOMALY": serializers.anomaly_result,
        "TEMPORAL": serializers.correlation_result,
        "CROSS_SOURCE": serializers.correlation_result,
        "NETWORK": serializers.network_result,
    }
    trace_signals = []
    for link in signals:
        model = _SIGNAL_MODELS[link.signal_type]
        row = db.get(model, link.signal_id)
        item = serializers.alert_signal(link)
        if row is not None:
            item["result"] = serializer_map[link.signal_type](row)
        trace_signals.append(item)

    features = db.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.analysis_run_id == alert.analysis_run_id,
            FeatureSnapshot.subject_id == alert.subject_id,
        )
    ).all()

    return {
        "alert": serializers.alert_summary(alert),
        "priority": serializers.priority_result(priority),
        "signals": trace_signals,
        "features": [serializers.feature_snapshot(f) for f in features],
        "traceable_chain": [
            "alert -> priority score -> signals (rule/anomaly/correlation/network) -> features -> raw events/reports",
        ],
    }


@router.patch("/alerts/{alert_id}/status", dependencies=[Depends(require_permissions(Permissions.ALERTS_REVIEW))])
def update_alert_status(
    alert_id: uuid.UUID,
    body: AlertStatusBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    new_status = body.status.upper()
    if new_status not in GENERIC_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid alert status")
    alert.status = new_status
    alert.triaged_at = datetime.now(timezone.utc)
    alert.triage_meta_json = {"action": "STATUS_CHANGE", "note": None, "by": str(user.id)}
    record_audit(
        db,
        actor_id=user.id,
        action=f"ALERT_STATUS_CHANGED_TO_{new_status}",
        entity_type="ALERT",
        entity_id=str(alert.id),
        metadata={"alert_ref": alert.alert_ref, "new_status": new_status},
    )
    db.commit()
    return serializers.alert_summary(alert)


def _triage(
    db: Session,
    alert: Alert,
    user: User,
    action: str,
    new_status: str,
    note: str | None,
) -> dict:
    """Apply an audited triage action to an alert."""
    priority = db.get(PriorityScore, alert.priority_score_id)
    alert.status = new_status
    alert.triaged_at = datetime.now(timezone.utc)
    alert.triage_meta_json = {"action": action, "note": note, "by": str(user.id)}
    record_audit(
        db,
        actor_id=user.id,
        action=action,
        entity_type="ALERT",
        entity_id=str(alert.id),
        metadata={
            "alert_ref": alert.alert_ref,
            "subject_id": str(alert.subject_id),
            "new_status": new_status,
            "priority_level": priority.priority_level if priority else None,
            "note": note,
        },
    )
    db.commit()
    return serializers.alert_summary(alert)


def _get_alert(db: Session, alert_id: uuid.UUID) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/{alert_id}/review", dependencies=[Depends(require_permissions(Permissions.ALERTS_REVIEW))])
def review_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    body: TriageNoteBody | None = None,
) -> dict:
    return _triage(db, _get_alert(db, alert_id), user, "ALERT_REVIEWED", "REVIEWED", body.note if body else None)


@router.post("/alerts/{alert_id}/dismiss", dependencies=[Depends(require_permissions(Permissions.ALERTS_DISMISS))])
def dismiss_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    body: TriageNoteBody | None = None,
) -> dict:
    return _triage(db, _get_alert(db, alert_id), user, "ALERT_DISMISSED", "DISMISSED", body.note if body else None)


@router.post("/alerts/{alert_id}/false-positive", dependencies=[Depends(require_permissions(Permissions.ALERTS_DISMISS))])
def false_positive_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    body: TriageNoteBody | None = None,
) -> dict:
    return _triage(db, _get_alert(db, alert_id), user, "ALERT_MARKED_FALSE_POSITIVE", "FALSE_POSITIVE", body.note if body else None)


@router.post("/alerts/{alert_id}/escalate", dependencies=[Depends(require_permissions(Permissions.ALERTS_REVIEW))])
def escalate_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    body: TriageNoteBody | None = None,
) -> dict:
    return _triage(db, _get_alert(db, alert_id), user, "ALERT_ESCALATED", "ESCALATED", body.note if body else None)


@router.post(
    "/alerts/{alert_id}/convert",
    dependencies=[
        Depends(require_permissions(Permissions.ALERTS_CONVERT)),
        Depends(require_permissions(Permissions.INVESTIGATIONS_CREATE)),
    ],
)
def convert_alert(
    alert_id: uuid.UUID,
    body: ConvertBody | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Convert a triaged alert into an investigation, preserving analytical context
    by reference (originating alert -> priority score -> signals -> raw records)."""
    alert = _get_alert(db, alert_id)
    if alert.status == "CONVERTED":
        raise HTTPException(status_code=409, detail="Alert already converted")
    if alert.subject_type != "ATHLETE":
        raise HTTPException(status_code=422, detail="Only athlete alerts can be converted")

    priority = db.get(PriorityScore, alert.priority_score_id)
    if priority is None:
        raise HTTPException(status_code=404, detail="Alert priority score missing")
    if priority.priority_level not in PRIORITY_LEVELS:
        raise HTTPException(status_code=422, detail="Unsupported priority level")

    priority_level = body.priority if body and body.priority else priority.priority_level
    if priority_level not in PRIORITY_LEVELS:
        raise HTTPException(status_code=422, detail="Unsupported priority level")

    title = (body.title if body and body.title else alert.title)[:255]
    note = body.note if body else None

    investigation = Investigation(
        title=title,
        description=f"Investigation opened from alert {alert.alert_ref} "
        f"({alert.subject_type} {str(alert.subject_id)[:8]}).",
        status="OPEN",
        priority=priority_level,
        subject_type=alert.subject_type,
        subject_id=alert.subject_id,
        originating_alert_id=alert.id,
        assigned_to=body.assigned_to if body else None,
        created_by=user.id,
    )
    db.add(investigation)
    db.flush()

    alert.status = "CONVERTED"
    alert.triaged_at = datetime.now(timezone.utc)
    alert.triage_meta_json = {"action": "ALERT_CONVERTED", "note": note, "by": str(user.id)}
    alert.investigation_id = investigation.id

    record_audit(
        db,
        actor_id=user.id,
        action="INVESTIGATION_CREATED",
        entity_type="INVESTIGATION",
        entity_id=str(investigation.id),
        metadata={
            "case_ref": investigation.case_ref,
            "originating_alert_id": str(alert.id),
            "subject_id": str(alert.subject_id),
            "priority": investigation.priority,
        },
    )
    record_audit(
        db,
        actor_id=user.id,
        action="ALERT_CONVERTED",
        entity_type="ALERT",
        entity_id=str(alert.id),
        metadata={
            "alert_ref": alert.alert_ref,
            "investigation_id": str(investigation.id),
            "note": note,
        },
    )
    db.commit()
    return {
        "alert": serializers.alert_summary(alert),
        "investigation": {
            "id": str(investigation.id),
            "case_ref": investigation.case_ref,
            "title": investigation.title,
            "status": investigation.status,
            "priority": investigation.priority,
        },
    }