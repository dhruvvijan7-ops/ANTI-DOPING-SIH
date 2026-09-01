"""Alerts API: listing, detail and traceability back to analysis results."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import serializers
from app.api.deps import require_permissions
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
from app.security.rbac import Permissions

router = APIRouter(tags=["alerts"])

_SIGNAL_MODELS = {
    "RULE": RuleResult,
    "ANOMALY": AnomalyResult,
    "TEMPORAL": CorrelationResult,
    "CROSS_SOURCE": CorrelationResult,
    "NETWORK": NetworkResult,
}


class AlertStatusBody(BaseModel):
    status: str


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
) -> dict:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    new_status = body.status.upper()
    if new_status not in {"NEW", "REVIEWED", "ACTIONED", "DISMISSED"}:
        raise HTTPException(status_code=422, detail="Invalid alert status")
    alert.status = new_status
    db.commit()
    return serializers.alert_summary(alert)