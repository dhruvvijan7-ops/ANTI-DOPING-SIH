"""Dict serializers for analytic ORM rows (API responses)."""
from __future__ import annotations

import uuid
from datetime import datetime


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def run_summary(run) -> dict:
    return {
        "run_id": str(run.id),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "status": run.status,
        "model": run.model,
        "model_version": run.model_version,
        "rule_version": run.rule_version,
        "feature_version": run.feature_version,
        "config": run.config_json,
        "result_count": run.result_count,
        "error": run.error,
    }


def feature_snapshot(snap) -> dict:
    return {
        "subject_id": str(snap.subject_id),
        "feature_id": snap.feature_id,
        "feature_version": snap.feature_version,
        "value": snap.value,
        "source_fields": snap.source_fields_json,
    }


def rule_result(row) -> dict:
    return {
        "id": str(row.id),
        "subject_id": str(row.subject_id),
        "rule_id": row.rule_id,
        "rule_version": row.rule_version,
        "name": row.name,
        "severity": row.severity,
        "weight": row.weight,
        "triggered": row.triggered,
        "detail": row.detail_json,
        "expression": row.expression,
    }


def anomaly_result(row) -> dict:
    return {
        "id": str(row.id),
        "subject_id": str(row.subject_id),
        "raw_score": row.raw_score,
        "normalized_score": row.normalized_score,
        "is_anomaly": row.is_anomaly,
        "contributions": row.contribution_json,
        "model_version": row.model_version,
        "feature_version": row.feature_version,
    }


def correlation_result(row) -> dict:
    return {
        "id": str(row.id),
        "subject_id": str(row.subject_id),
        "correlation_type": row.correlation_type,
        "window_days": row.window_days,
        "score": row.score,
        "signal_count": row.signal_count,
        "category_count": row.category_count,
        "signal_ids": row.signal_ids_json,
        "description": row.description,
    }


def network_result(row) -> dict:
    return {
        "id": str(row.id),
        "subject_id": str(row.subject_id),
        "degree": row.degree,
        "weighted_degree": row.weighted_degree,
        "relationship_diversity": row.relationship_diversity,
        "connected_priority_count": row.connected_priority_count,
        "score": row.score,
        "detail": row.detail_json,
    }


def priority_result(row) -> dict:
    return {
        "id": str(row.id),
        "subject_id": str(row.subject_id),
        "overall_score": row.overall_score,
        "priority_level": row.priority_level,
        "rule_score": row.rule_score,
        "anomaly_score": row.anomaly_score,
        "correlation_score": row.correlation_score,
        "temporal_score": row.temporal_score,
        "network_score": row.network_score,
        "source_quality_score": row.source_quality_score,
        "explanation": row.explanation,
        "components": row.components_json,
    }


def alert_summary(row) -> dict:
    return {
        "id": str(row.id),
        "alert_ref": row.alert_ref,
        "analysis_run_id": str(row.analysis_run_id),
        "subject_type": row.subject_type,
        "subject_id": str(row.subject_id),
        "score": row.score,
        "priority_level": row.priority_level,
        "title": row.title,
        "status": row.status,
        "created_at": _iso(row.created_at),
    }


def alert_signal(row) -> dict:
    return {
        "id": str(row.id),
        "signal_type": row.signal_type,
        "signal_id": str(row.signal_id),
        "contributed": row.contributed,
    }