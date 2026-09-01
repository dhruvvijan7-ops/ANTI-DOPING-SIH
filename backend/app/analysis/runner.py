"""Analysis runner: orchestrates the whole pipeline and persists every stage.

The runner is the single integration point used by the API and the CLI. It records
one AnalysisRun with the model/rule/feature versions and the configuration actually
used, then saves features, rule/anomaly/correlation/network results, priority scores
and alerts so that every alert is traceable to the raw records that produced it.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis import correlation, network as network_mod
from app.analysis.anomaly import AnomalyOutcome, detect_anomalies
from app.analysis.contracts import (
    PRIORITY_LEVELS,
    AnalysisConfig,
    CorrelationOutcome,
    PriorityOutcome,
    RuleOutcome,
    SubjectData,
)
from app.analysis.features import FeatureValue, compute_features, feature_catalog
from app.analysis.priority import build_explanation, compute_priority, compute_source_quality_score
from app.analysis.repository import load_subjects
from app.analysis.rules import evaluate_rules, rule_catalog
from app.models.analytics import (
    Alert,
    AlertSignal,
    AnalysisRun,
    AnomalyResult,
    CorrelationResult,
    FeatureSnapshot,
    FeatureVersion,
    NetworkResult,
    PriorityScore,
    RuleResult,
    RuleVersion,
)


class AnalysisError(RuntimeError):
    """Fatal engine failure; the run is marked FAILED before re-raising."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sync_catalogs(db: Session) -> None:
    """Idempotently persist the feature + rule version catalogs (drives enabled-switches)."""
    for row in feature_catalog():
        exists = db.scalar(
            select(FeatureVersion).where(
                FeatureVersion.identifier == row["identifier"],
                FeatureVersion.version == row["version"],
            )
        )
        if exists is None:
            db.add(FeatureVersion(**row))
    for row in rule_catalog():
        exists = db.scalar(
            select(RuleVersion).where(
                RuleVersion.rule_id == row["rule_id"],
                RuleVersion.version == row["version"],
            )
        )
        if exists is None:
            db.add(RuleVersion(**row))
    db.flush()


def _alert_threshold_score(cfg: AnalysisConfig) -> float:
    level = (cfg.alert_threshold or "HIGH").upper()
    if level not in PRIORITY_LEVELS:
        level = "HIGH"
    return float(PRIORITY_LEVELS[level][0])


def run_analysis(
    db: Session,
    config: AnalysisConfig | None = None,
    subject_ids: list[uuid.UUID] | None = None,
    user_id: uuid.UUID | None = None,
) -> AnalysisRun:
    cfg = config or AnalysisConfig()
    run = AnalysisRun(
        started_at=_now(),
        status="RUNNING",
        model="ISOLATION_FOREST",
        model_version=str(cfg.isolation_forest["model_version"]),
        rule_version=cfg.rule_version,
        feature_version=cfg.feature_version,
        config_json=cfg.to_dict(),
        created_by=user_id,
    )
    db.add(run)
    db.flush()
    try:
        sync_catalogs(db)
        db.flush()

        subjects = load_subjects(db, subject_ids)
        if not subjects:
            run.status = "COMPLETED"
            run.finished_at = _now()
            run.result_count = 0
            db.commit()
            return run

        as_of = date.today()

        # --- stage 5: features -------------------------------------------------
        features_by_subject: dict[uuid.UUID, dict[str, FeatureValue]] = {}
        for subject in subjects:
            feats = compute_features(subject, cfg, as_of)
            features_by_subject[subject.subject_id] = feats
            for fid, fv in feats.items():
                db.add(
                    FeatureSnapshot(
                        analysis_run_id=run.id,
                        subject_type=subject.subject_type,
                        subject_id=subject.subject_id,
                        feature_id=fid,
                        feature_version=fv.version,
                        value=fv.value,
                        source_fields_json=fv.source_fields,
                    )
                )

        # --- stage 6: rules ----------------------------------------------------
        rule_outcomes: dict[uuid.UUID, tuple[list[RuleOutcome], float]] = {}
        for subject in subjects:
            outcomes, rule_score = evaluate_rules(
                subject, features_by_subject[subject.subject_id], cfg, as_of
            )
            rule_outcomes[subject.subject_id] = (outcomes, rule_score)
            for o in outcomes:
                db.add(
                    RuleResult(
                        analysis_run_id=run.id,
                        subject_type=subject.subject_type,
                        subject_id=subject.subject_id,
                        rule_id=o.rule_id,
                        rule_version=o.version,
                        name=o.name,
                        severity=o.severity,
                        weight=o.weight,
                        triggered=o.triggered,
                        detail_json=o.detail,
                        expression=o.expression,
                    )
                )

        # --- stage 7: isolation forest ----------------------------------------
        order = sorted(subjects, key=lambda s: str(s.subject_id))
        samples = [
            (
                s.subject_id,
                {fid: fv.value for fid, fv in features_by_subject[s.subject_id].items()},
            )
            for s in order
        ]
        anomaly_outcomes, _model_info = detect_anomalies(samples, cfg)
        anomalies_by_subject: dict[uuid.UUID, AnomalyOutcome] = {
            o.subject_id: o for o in anomaly_outcomes
        }
        for o in anomaly_outcomes:
            db.add(
                AnomalyResult(
                    analysis_run_id=run.id,
                    subject_type="ATHLETE",
                    subject_id=o.subject_id,
                    raw_score=o.raw_score,
                    normalized_score=o.normalized_score,
                    is_anomaly=o.is_anomaly,
                    contribution_json={
                        c.feature_id: {
                            "contribution": c.contribution,
                            "std_value": c.std_value,
                            "value": c.actual_value,
                        }
                        for c in o.contributions
                    },
                    model_version=o.model_version,
                    feature_version=cfg.feature_version,
                )
            )

        # --- stages 8-9: temporal + cross-source correlation --------------------
        temporal_by_subject: dict[uuid.UUID, CorrelationOutcome] = {}
        cross_by_subject: dict[uuid.UUID, CorrelationOutcome] = {}
        for subject in subjects:
            temporal = correlation.temporal_correlation(subject, cfg, as_of)
            cross = correlation.cross_source_correlation(subject, cfg, as_of)
            temporal_by_subject[subject.subject_id] = temporal
            cross_by_subject[subject.subject_id] = cross
            for kind, outcome in (("TEMPORAL", temporal), ("CROSS_SOURCE", cross)):
                db.add(
                    CorrelationResult(
                        analysis_run_id=run.id,
                        correlation_type=kind,
                        subject_type=subject.subject_type,
                        subject_id=subject.subject_id,
                        window_days=outcome.window_days,
                        score=outcome.score,
                        signal_count=outcome.signal_count,
                        category_count=outcome.category_count,
                        signal_ids_json=[str(s) for s in outcome.signal_ids],
                        description=outcome.description,
                    )
                )

        # --- stages 10-11: network relevance + priority ------------------------
        # Pass A: provisional priorities without the connected-bonus term, so we can
        # determine which neighbors are themselves high priority within the run.
        provisional: dict[uuid.UUID, float] = {}
        for subject in subjects:
            fv = features_by_subject[subject.subject_id]
            rule_score = rule_outcomes[subject.subject_id][1]
            anomaly = anomalies_by_subject[subject.subject_id]
            temporal = temporal_by_subject[subject.subject_id]
            cross = cross_by_subject[subject.subject_id]
            network = network_mod.network_relevance(subject, cfg, as_of, priorities={})
            source_quality = compute_source_quality_score(fv)
            priority = compute_priority(
                subject.subject_id,
                rule_score,
                anomaly.normalized_score,
                cross.score,
                temporal.score,
                network,
                source_quality,
            )
            provisional[subject.subject_id] = priority.overall

        priority_by_subject: dict[uuid.UUID, PriorityOutcome] = {}
        for subject in subjects:
            fv = features_by_subject[subject.subject_id]
            rule_score = rule_outcomes[subject.subject_id][1]
            anomaly = anomalies_by_subject[subject.subject_id]
            temporal = temporal_by_subject[subject.subject_id]
            cross = cross_by_subject[subject.subject_id]
            network = network_mod.network_relevance(subject, cfg, as_of, priorities=provisional)
            source_quality = compute_source_quality_score(fv)
            priority = compute_priority(
                subject.subject_id,
                rule_score,
                anomaly.normalized_score,
                cross.score,
                temporal.score,
                network,
                source_quality,
            )
            priority.explanation = build_explanation(
                subject_type=subject.subject_type,
                subject_ref=str(subject.subject_id),
                priority_components={
                    **priority.components,
                    "overall_score": priority.overall,
                    "priority_level": priority.level,
                },
                rule_results=[o for o in rule_outcomes[subject.subject_id][0]],
                anomaly_contributions=anomaly.contributions,
                temporal=temporal,
                cross_source=cross,
                network=network,
                features=fv,
            )
            priority_by_subject[subject.subject_id] = priority
            db.add(
                NetworkResult(
                    analysis_run_id=run.id,
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    degree=network.degree,
                    weighted_degree=network.weighted_degree,
                    relationship_diversity=network.relationship_diversity,
                    connected_priority_count=network.connected_priority_count,
                    score=network.score,
                    detail_json=network.detail,
                )
            )
            db.add(
                PriorityScore(
                    analysis_run_id=run.id,
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    overall_score=priority.overall,
                    priority_level=priority.level,
                    rule_score=priority.rule_score,
                    anomaly_score=priority.anomaly_score,
                    correlation_score=priority.correlation_score,
                    temporal_score=priority.temporal_score,
                    network_score=priority.network_score,
                    source_quality_score=priority.source_quality_score,
                    explanation=priority.explanation,
                    components_json=priority.components,
                )
            )
        db.flush()  # materialize ids of results for alert links

        # --- stage 13: alerts ---------------------------------------------------
        alert_threshold_score = _alert_threshold_score(cfg)
        alert_count = 0
        for subject in subjects:
            priority = priority_by_subject[subject.subject_id]
            if priority.overall < alert_threshold_score:
                continue
            alert = Alert(
                alert_ref=f"ALERT-{uuid.uuid4().hex[:12].upper()}",
                analysis_run_id=run.id,
                priority_score_id=db.scalar(
                    select(PriorityScore.id).where(
                        PriorityScore.analysis_run_id == run.id,
                        PriorityScore.subject_id == subject.subject_id,
                    )
                ),
                subject_type=subject.subject_type,
                subject_id=subject.subject_id,
                score=priority.overall,
                priority_level=priority.level,
                title=f"{subject.subject_type} {str(subject.subject_id)[:8]} - {priority.level} priority ({priority.overall:.0f}/100)",
                status="NEW",
            )
            db.add(alert)
            db.flush()
            signal_links: list[tuple[str, uuid.UUID]] = []
            for o in rule_outcomes[subject.subject_id][0]:
                if o.triggered:
                    signal_links.append(("RULE", db.scalar(
                        select(RuleResult.id).where(
                            RuleResult.analysis_run_id == run.id,
                            RuleResult.subject_id == subject.subject_id,
                            RuleResult.rule_id == o.rule_id,
                        )
                    )))
            anomaly = anomalies_by_subject[subject.subject_id]
            if anomaly.is_anomaly or anomaly.normalized_score >= alert_threshold_score * 0.5:
                signal_links.append(("ANOMALY", db.scalar(
                    select(AnomalyResult.id).where(
                        AnomalyResult.analysis_run_id == run.id,
                        AnomalyResult.subject_id == subject.subject_id,
                    )
                )))
            temporal = temporal_by_subject[subject.subject_id]
            cross = cross_by_subject[subject.subject_id]
            if temporal.signal_count:
                signal_links.append(("TEMPORAL", db.scalar(
                    select(CorrelationResult.id).where(
                        CorrelationResult.analysis_run_id == run.id,
                        CorrelationResult.subject_id == subject.subject_id,
                        CorrelationResult.correlation_type == "TEMPORAL",
                    )
                )))
            if cross.signal_count:
                signal_links.append(("CROSS_SOURCE", db.scalar(
                    select(CorrelationResult.id).where(
                        CorrelationResult.analysis_run_id == run.id,
                        CorrelationResult.subject_id == subject.subject_id,
                        CorrelationResult.correlation_type == "CROSS_SOURCE",
                    )
                )))
            network = network_mod.network_relevance(subject, cfg, as_of, priorities=provisional)
            if network.degree:
                signal_links.append(("NETWORK", db.scalar(
                    select(NetworkResult.id).where(
                        NetworkResult.analysis_run_id == run.id,
                        NetworkResult.subject_id == subject.subject_id,
                    )
                )))
            for sig_type, sig_id in signal_links:
                if sig_id is not None:
                    db.add(
                        AlertSignal(
                            alert_id=alert.id,
                            signal_type=sig_type,
                            signal_id=sig_id,
                            contributed=True,
                        )
                    )
            alert_count += 1

        run.status = "COMPLETED"
        run.finished_at = _now()
        run.result_count = len(subjects)
        db.commit()
        return run
    except Exception as exc:  # noqa: BLE001 - persist the failure on the run record
        db.rollback()
        run.status = "FAILED"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = _now()
        db.commit()
        raise AnalysisError(f"Analysis run {run.id} failed: {exc}") from exc