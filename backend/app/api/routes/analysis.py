"""Analytics API: run management and per-stage result retrieval."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis import serializers
from app.analysis.contracts import AnalysisConfig
from app.analysis.runner import AnalysisError, run_analysis
from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.analytics import (
    AnalysisRun,
    AnomalyResult,
    CorrelationResult,
    FeatureSnapshot,
    NetworkResult,
    PriorityScore,
    RuleResult,
)
from app.models.identity import User
from app.security.rbac import Permissions

router = APIRouter(tags=["analytics"])


class RunCreate(BaseModel):
    subject_ids: list[uuid.UUID] | None = None
    alert_threshold: str | None = Field(default="HIGH", pattern="^(LOW|MODERATE|HIGH|VERY_HIGH|CRITICAL)$")
    temporal_window_days: int | None = Field(default=None, ge=1, le=365)
    cross_source_window_days: int | None = Field(default=None, ge=1, le=730)


@router.post("/analysis/runs", status_code=status.HTTP_201_CREATED)
def start_run(
    body: RunCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(Permissions.ANALYSIS_RUN)),
) -> dict:
    cfg = AnalysisConfig(
        alert_threshold=body.alert_threshold or "HIGH",
        temporal_window_days=body.temporal_window_days or 45,
        cross_source_window_days=body.cross_source_window_days or 90,
    )
    try:
        run = run_analysis(db, config=cfg, subject_ids=body.subject_ids, user_id=user.id)
    except AnalysisError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return serializers.run_summary(run)


@router.get("/analysis/runs", dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def list_runs(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query()] = 50,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> dict:
    stmt = select(AnalysisRun)
    if status_filter:
        stmt = stmt.where(AnalysisRun.status == status_filter.upper())
    stmt = stmt.order_by(AnalysisRun.started_at.desc()).limit(min(limit, 200))
    runs = db.scalars(stmt).all()
    return {"count": len(runs), "runs": [serializers.run_summary(r) for r in runs]}


def _get_run(db: Session, run_id: uuid.UUID) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run


@router.get("/analysis/runs/{run_id}", dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_detail(run_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    run = _get_run(db, run_id)
    counts: dict[str, int] = {}
    for model, key in (
        (FeatureSnapshot, "features"),
        (RuleResult, "rules"),
        (AnomalyResult, "anomalies"),
        (CorrelationResult, "correlations"),
        (NetworkResult, "network"),
        (PriorityScore, "priority"),
    ):
        counts[key] = db.scalar(
            select(func.count()).select_from(model).where(model.analysis_run_id == run_id)
        ) or 0
    return {**serializers.run_summary(run), "result_counts": counts}


@router.get("/analysis/runs/{run_id}/features",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_features(
    run_id: uuid.UUID,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_run(db, run_id)
    stmt = select(FeatureSnapshot).where(FeatureSnapshot.analysis_run_id == run_id)
    if subject_id:
        stmt = stmt.where(FeatureSnapshot.subject_id == subject_id)
    rows = db.scalars(stmt.order_by(FeatureSnapshot.subject_id, FeatureSnapshot.feature_id)).all()
    return {"count": len(rows), "features": [serializers.feature_snapshot(r) for r in rows]}


@router.get("/analysis/runs/{run_id}/rules",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_rules(
    run_id: uuid.UUID,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    only_triggered: Annotated[bool, Query()] = False,
    db: Session = Depends(get_db),
) -> dict:
    _get_run(db, run_id)
    stmt = select(RuleResult).where(RuleResult.analysis_run_id == run_id)
    if subject_id:
        stmt = stmt.where(RuleResult.subject_id == subject_id)
    if only_triggered:
        stmt = stmt.where(RuleResult.triggered.is_(True))
    rows = db.scalars(stmt.order_by(RuleResult.subject_id, RuleResult.rule_id)).all()
    return {"count": len(rows), "rules": [serializers.rule_result(r) for r in rows]}


@router.get("/analysis/runs/{run_id}/anomalies",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_anomalies(
    run_id: uuid.UUID,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_run(db, run_id)
    stmt = select(AnomalyResult).where(AnomalyResult.analysis_run_id == run_id)
    if subject_id:
        stmt = stmt.where(AnomalyResult.subject_id == subject_id)
    rows = db.scalars(stmt.order_by(AnomalyResult.normalized_score.desc())).all()
    return {"count": len(rows), "anomalies": [serializers.anomaly_result(r) for r in rows]}


@router.get("/analysis/runs/{run_id}/correlations",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_correlations(
    run_id: uuid.UUID,
    correlation_type: Annotated[str | None, Query()] = None,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_run(db, run_id)
    stmt = select(CorrelationResult).where(CorrelationResult.analysis_run_id == run_id)
    if correlation_type:
        stmt = stmt.where(CorrelationResult.correlation_type == correlation_type.upper())
    if subject_id:
        stmt = stmt.where(CorrelationResult.subject_id == subject_id)
    rows = db.scalars(stmt.order_by(CorrelationResult.correlation_type, CorrelationResult.subject_id)).all()
    return {"count": len(rows), "correlations": [serializers.correlation_result(r) for r in rows]}


@router.get("/analysis/runs/{run_id}/network",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_network(
    run_id: uuid.UUID,
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_run(db, run_id)
    stmt = select(NetworkResult).where(NetworkResult.analysis_run_id == run_id)
    if subject_id:
        stmt = stmt.where(NetworkResult.subject_id == subject_id)
    rows = db.scalars(stmt.order_by(NetworkResult.score.desc())).all()
    return {"count": len(rows), "network": [serializers.network_result(r) for r in rows]}


@router.get("/analysis/runs/{run_id}/priority",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def run_priority(
    run_id: uuid.UUID,
    min_level: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_run(db, run_id)
    stmt = select(PriorityScore).where(PriorityScore.analysis_run_id == run_id)
    if min_level:
        stmt = stmt.where(PriorityScore.priority_level == min_level.upper())
    rows = db.scalars(stmt.order_by(PriorityScore.overall_score.desc())).all()
    return {"count": len(rows), "priority": [serializers.priority_result(r) for r in rows]}


@router.get("/analysis/subjects/{subject_id}/results",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def subject_results(
    subject_id: uuid.UUID,
    run_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(PriorityScore).where(PriorityScore.subject_id == subject_id)
    if run_id:
        stmt = stmt.where(PriorityScore.analysis_run_id == run_id)
    rows = db.scalars(stmt.order_by(PriorityScore.overall_score.desc()).limit(10)).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No priority results for subject")
    latest = rows[0]
    run = _get_run(db, latest.analysis_run_id)
    features = db.scalars(
        select(FeatureSnapshot).where(
            FeatureSnapshot.analysis_run_id == run.id,
            FeatureSnapshot.subject_id == subject_id,
        )
    ).all()
    return {
        "priority": serializers.priority_result(latest),
        "feature_version": run.feature_version,
        "features": [serializers.feature_snapshot(r) for r in features],
    }


@router.get("/analysis/subjects/{subject_id}/features",
            dependencies=[Depends(require_permissions(Permissions.ANALYSIS_READ))])
def subject_features(
    subject_id: uuid.UUID,
    run_id: Annotated[uuid.UUID | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(FeatureSnapshot).where(FeatureSnapshot.subject_id == subject_id)
    if run_id:
        stmt = stmt.where(FeatureSnapshot.analysis_run_id == run_id)
    rows = db.scalars(stmt.order_by(FeatureSnapshot.analysis_run_id)).all()
    return {"count": len(rows), "features": [serializers.feature_snapshot(r) for r in rows]}