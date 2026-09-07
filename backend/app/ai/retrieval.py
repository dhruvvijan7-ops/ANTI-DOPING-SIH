"""Retrieval: assemble exactly the case data an AI operation is permitted to see.

The context is a projection of *this investigation only*: originating alert,
its resolved analytical signals, the subject's events/reports/relationships plus
the human case work (evidence, notes, findings, tasks). No subject other than the
case subject is included, satisfying the "do not send unrelated data" rule.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.models.audit import AuditEvent
from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.intelligence import IntelligenceReport
from app.models.investigations import Investigation
from app.models.relationships import EntityRelationship
from app.models.subjects import Athlete

_SIGNAL_MODELS = {
    "RULE": RuleResult,
    "ANOMALY": AnomalyResult,
    "TEMPORAL": CorrelationResult,
    "CROSS_SOURCE": CorrelationResult,
    "NETWORK": NetworkResult,
}


@dataclass
class CaseContext:
    investigation_id: str
    case_ref: str
    title: str
    status: str
    priority: str
    subject_type: str
    subject_id: str
    subject_label: str = ""
    alert_ref: str | None = None
    alert_level: str | None = None
    alert_score: float | None = None
    signals: list[dict] = field(default_factory=list)
    features: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    intelligence: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    tasks: list[dict] = field(default_factory=list)
    audit_count: int = 0


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _event_rows(db: Session, model, athlete_id: uuid.UUID) -> list:
    return list(db.scalars(select(model).where(model.athlete_id == athlete_id)).all())


def build_case_context(db: Session, inv: Investigation) -> CaseContext:
    ctx = CaseContext(
        investigation_id=str(inv.id),
        case_ref=inv.case_ref,
        title=inv.title,
        status=inv.status,
        priority=inv.priority,
        subject_type=inv.subject_type,
        subject_id=str(inv.subject_id),
    )

    if inv.subject_type == "ATHLETE":
        athlete = db.get(Athlete, inv.subject_id)
        if athlete is not None:
            ctx.subject_label = f"{athlete.first_name or ''} {athlete.last_name or ''}".strip() or "ATH-" + str(inv.subject_id)[:8]

    alert = None
    if inv.originating_alert_id:
        alert = db.get(Alert, inv.originating_alert_id)
    if alert is not None:
        ctx.alert_ref = alert.alert_ref
        ctx.alert_level = alert.priority_level
        ctx.alert_score = alert.score
        priority = db.get(PriorityScore, alert.priority_score_id)
        if priority is not None:
            ctx.features.append({
                "source": "priority",
                "overall_score": priority.overall_score,
                "rule_score": priority.rule_score,
                "anomaly_score": priority.anomaly_score,
                "correlation_score": priority.correlation_score,
                "temporal_score": priority.temporal_score,
                "network_score": priority.network_score,
                "source_quality_score": priority.source_quality_score,
            })
        for link in db.scalars(select(AlertSignal).where(AlertSignal.alert_id == alert.id)).all():
            model = _SIGNAL_MODELS.get(link.signal_type)
            row = db.get(model, link.signal_id) if model else None
            if row is None:
                continue
            ctx.signals.append(_signal_context(link.signal_type, row))
        if priority is not None:
            anomalies = db.scalars(
                select(AnomalyResult).where(
                    AnomalyResult.analysis_run_id == alert.analysis_run_id,
                    AnomalyResult.subject_id == alert.subject_id,
                )
            ).all()
            for a in anomalies:
                for feature_id, contrib in (a.contribution_json or {}).items():
                    ctx.features.append({
                        "feature_id": feature_id,
                        "contribution": contrib.get("contribution") if isinstance(contrib, dict) else None,
                        "value": contrib.get("value") if isinstance(contrib, dict) else None,
                    })

    for sig in _event_rows(db, TestingEvent, inv.subject_id):
        ctx.events.append({"category": "TESTING", "occurred_on": sig.test_date.isoformat(), "detail": sig.test_type or sig.result_classification or ""})
    for sig in _event_rows(db, BiologicalObservation, inv.subject_id):
        ctx.events.append({"category": "BIOLOGICAL", "occurred_on": sig.observation_date.isoformat(), "detail": sig.marker or ""})
    for sig in _event_rows(db, WhereaboutsEvent, inv.subject_id):
        ctx.events.append({"category": "WHEREABOUTS", "occurred_on": sig.event_date.isoformat(), "detail": sig.status or ""})
    for sig in _event_rows(db, TravelEvent, inv.subject_id):
        ctx.events.append({"category": "TRAVEL", "occurred_on": sig.event_date.isoformat(), "detail": (sig.origin or "") + " -> " + (sig.destination or "")})
    for sig in _event_rows(db, MedicalEvent, inv.subject_id):
        ctx.events.append({"category": "MEDICAL", "occurred_on": sig.event_date.isoformat() if sig.event_date else "", "detail": sig.event_type or ""})
    for sig in _event_rows(db, SupplementEvent, inv.subject_id):
        ctx.events.append({"category": "SUPPLEMENT", "occurred_on": sig.event_date.isoformat() if sig.event_date else "", "detail": sig.usage_note or ""})

    for r in db.scalars(
        select(IntelligenceReport).where(
            IntelligenceReport.subject_type == inv.subject_type,
            IntelligenceReport.subject_id == inv.subject_id,
        )
    ).all():
        ctx.intelligence.append({
            "title": r.title,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "reliability": r.reliability,
            "info_category": r.info_category,
            "source": r.source.name if r.source else None,
        })

    for rel in db.scalars(
        select(EntityRelationship).where(
            (EntityRelationship.from_entity_type == inv.subject_type)
            & (EntityRelationship.from_entity_id == inv.subject_id)
            | (EntityRelationship.to_entity_type == inv.subject_type)
            & (EntityRelationship.to_entity_id == inv.subject_id)
        )
    ).all():
        rel_name = rel.rel_type.name if rel.rel_type else "UNKNOWN"
        other = f"{rel.to_entity_type}:{rel.to_entity_id}" if rel.from_entity_id == inv.subject_id else f"{rel.from_entity_type}:{rel.from_entity_id}"
        ctx.relationships.append({
            "type": rel_name,
            "other_entity": other,
            "confidence": rel.confidence,
        })

    for e in inv.evidence:
        ctx.evidence.append({
            "id": str(e.id),
            "title": e.title,
            "evidence_type": e.evidence_type,
            "classification": e.classification,
            "source": e.source,
            "item_date": _iso(e.item_date),
        })
    for n in inv.notes:
        ctx.notes.append({"author": n.author.full_name if n.author else None, "content": n.content, "created_at": _iso(n.created_at)})
    for f in inv.findings:
        ctx.findings.append({
            "id": str(f.id),
            "title": f.title,
            "statement": f.statement,
            "assessment": f.assessment,
            "confident": f.confident,
        })
    for t in inv.tasks:
        ctx.tasks.append({"title": t.title, "status": t.status})

    audit_stmt = select(AuditEvent).where(
        (AuditEvent.entity_type == "INVESTIGATION") & (AuditEvent.entity_id == str(inv.id))
    )
    ctx.audit_count = len(db.scalars(audit_stmt).all())
    return ctx


def _signal_context(signal_type: str, row) -> dict:
    if signal_type == "RULE":
        return {
            "type": "RULE",
            "rule_id": row.rule_id,
            "name": row.name,
            "severity": row.severity,
            "triggered": row.triggered,
            "expression": row.expression,
            "detail": row.detail_json,
        }
    if signal_type == "ANOMALY":
        contribs = []
        for fid, c in (row.contribution_json or {}).items():
            if isinstance(c, dict):
                contribs.append({"feature": fid, "contribution": c.get("contribution"), "value": c.get("value")})
        return {
            "type": "ANOMALY",
            "normalized_score": row.normalized_score,
            "is_anomaly": row.is_anomaly,
            "contributions": contribs,
        }
    if signal_type in ("TEMPORAL", "CROSS_SOURCE"):
        return {
            "type": signal_type,
            "score": row.score,
            "signal_count": row.signal_count,
            "window_days": row.window_days,
            "category_count": row.category_count,
            "description": row.description,
        }
    if signal_type == "NETWORK":
        return {
            "type": "NETWORK",
            "score": row.score,
            "degree": row.degree,
            "weighted_degree": row.weighted_degree,
            "connected_priority_count": row.connected_priority_count,
        }
    return {"type": signal_type}