"""Priority scoring and explanation assembly (pipeline stage 11-12).

Priority = 0.25*Rule + 0.20*Anomaly + 0.20*CrossSource + 0.15*Temporal + 0.10*Network
+ 0.10*SourceQuality, normalized to 0-100 and classified as LOW/MODERATE/HIGH/
VERY_HIGH/CRITICAL. The explanation is assembled deterministically from the actual
computed component values and the records that produced them.
"""
from __future__ import annotations

import uuid

from app.analysis.contracts import (
    PRIORITY_WEIGHTS,
    AnalysisConfig,
    CorrelatedCluster,
    FeatureValue,
    NetworkOutcome,
    PriorityOutcome,
)
from app.analysis.features import reliability_weight

SOURCE_QUALITY_NEUTRAL = 50.0  # no reporting evidence: neutral, not penalized/boosted
STANDARD_DEVIATION_WARNING = 2.5


def compute_source_quality_score(features: dict[str, FeatureValue]) -> float:
    fv = features.get("report_reliability_weighted")
    if fv is None or fv.value == 0.0:
        return SOURCE_QUALITY_NEUTRAL
    # Weights range 0.1..1.0; spread to 0..100 (A = 100, F = 0).
    return round(max(1.0, min(100.0, (fv.value - 0.1) / 0.9 * 100.0)), 2)


def compute_priority(
    subject_id: uuid.UUID,
    rule_score: float,
    anomaly_score: float,
    cross_source_score: float,
    temporal_score: float,
    network: NetworkOutcome,
    source_quality_score: float,
) -> PriorityOutcome:
    overall = (
        PRIORITY_WEIGHTS["rule"] * rule_score
        + PRIORITY_WEIGHTS["anomaly"] * anomaly_score
        + PRIORITY_WEIGHTS["correlation"] * cross_source_score
        + PRIORITY_WEIGHTS["temporal"] * temporal_score
        + PRIORITY_WEIGHTS["network"] * network.score
        + PRIORITY_WEIGHTS["source_quality"] * source_quality_score
    )
    overall = round(max(0.0, min(100.0, overall)), 2)

    from app.analysis.contracts import priority_level_for

    level = priority_level_for(overall)
    return PriorityOutcome(
        subject_id=subject_id,
        overall=overall,
        level=level,
        rule_score=rule_score,
        anomaly_score=anomaly_score,
        correlation_score=cross_source_score,
        temporal_score=temporal_score,
        network_score=network.score,
        source_quality_score=source_quality_score,
        explanation="",
        components={
            "rule_score": rule_score,
            "anomaly_score": anomaly_score,
            "cross_source_score": cross_source_score,
            "temporal_score": temporal_score,
            "network_score": network.score,
            "source_quality_score": source_quality_score,
            "weights": PRIORITY_WEIGHTS,
        },
    )


def build_explanation(
    subject_type: str,
    subject_ref: str,
    priority_components: dict,
    rule_results: list,
    anomaly_contributions: list[FeatureValue] | list,
    temporal: object,
    cross_source: object,
    network: NetworkOutcome,
    features: dict[str, FeatureValue],
) -> str:
    """Assemble a deterministic, defensible summary from actual computed values."""
    c = priority_components
    parts = [
        f"{subject_type} {subject_ref} scored {c['rule_score']:.0f}/100 on rules, "
        f"{c['anomaly_score']:.0f}/100 on anomaly, "
        f"{c['cross_source_score']:.0f}/100 on cross-source, "
        f"{c['temporal_score']:.0f}/100 on temporal correlation, "
        f"{c['network_score']:.0f}/100 on network relevance, "
        f"{c['source_quality_score']:.0f}/100 on source quality "
        f"(overall {c['overall_score']:.1f}/100, {c['priority_level']}).",
    ]

    fired = [r for r in rule_results if r.triggered]
    if fired:
        parts.append(
            "Triggered rules: "
            + "; ".join(f"{r.rule_id} {r.name} ({r.severity})" for r in fired)
            + "."
        )

    top = list(anomaly_contributions)[:3]
    if top:
        parts.append(
            "Anomaly drivers: "
            + "; ".join(
                f"{t.feature_id}={t.actual_value} (z={t.std_value:+.2f})" for t in top
            )
            + "."
        )

    if temporal is not None and getattr(temporal, "signal_count", 0):
        parts.append(
            f"Temporal: {temporal.signal_count} signals across {temporal.category_count} "
            f"categories within the {temporal.window_days}-day window."
        )
    if cross_source is not None and getattr(cross_source, "signal_count", 0):
        parts.append(
            f"Cross-source: {cross_source.signal_count} deduplicated reports from "
            f"{cross_source.category_count} independent source categories "
            f"(duplicates counted once)."
        )
    parts.append(
        f"Network: degree {network.degree}, {network.relationship_diversity} relationship "
        f"type(s), {network.connected_priority_count} connected high-priority entity/entities."
    )
    return " ".join(parts)