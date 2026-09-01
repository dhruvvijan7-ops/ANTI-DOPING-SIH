"""Unit tests for the Isolation Forest detector and its explanations."""
from __future__ import annotations

import uuid

from app.analysis.anomaly import detect_anomalies
from app.analysis.contracts import AnalysisConfig

CFG = AnalysisConfig()

_SAMPLE_KEYS = [
    "event_frequency",
    "frequency_change",
    "mean_interval_days",
    "min_interval_days",
    "temporal_cluster_count",
    "longitudinal_deviation_abs",
    "source_diversity",
    "corroboration_count",
    "relationship_degree",
    "relationship_diversity",
]


def _sample(values: dict[str, float]) -> tuple[uuid.UUID, dict[str, float]]:
    return uuid.uuid4(), dict(values)


def _flat(subject_n: int, events: float) -> tuple[uuid.UUID, dict[str, float]]:
    return (
        uuid.uuid4(),
        {
            "event_frequency": events,
            "frequency_change": 0.0,
            "mean_interval_days": 30.0,
            "min_interval_days": 14.0,
            "temporal_cluster_count": 0.0,
            "longitudinal_deviation_abs": 0.1,
            "source_diversity": 1.0,
            "corroboration_count": 0.0,
            "relationship_degree": 0.0,
            "relationship_diversity": 0.0,
        },
    )


def test_scores_within_range():
    samples = [_flat(i, float(2 + i)) for i in range(10)]
    outcomes, _ = detect_anomalies(samples, CFG)
    assert len(outcomes) == 10
    for o in outcomes:
        assert 0.0 <= o.normalized_score <= 100.0


def test_reproducible_output():
    samples = [
        _flat(i, float(1 + i * 14)) for i in range(12)
    ] + [
        (
            uuid.uuid4(),
            {
                **_flat(0, 3.0)[1],
                "temporal_cluster_count": 8.0,
                "longitudinal_deviation_abs": 6.0,
                "source_diversity": 6.0,
                "corroboration_count": 5.0,
            },
        )
    ]
    a = detect_anomalies(samples, CFG)[0]
    b = detect_anomalies(samples, CFG)[0]
    for x, y in zip(a, b):
        assert x.raw_score == y.raw_score
        assert x.normalized_score == y.normalized_score
        assert x.is_anomaly == y.is_anomaly
    assert sum(1 for x in a if x.is_anomaly) >= 1  # the outlier is flagged


def test_scenario_ranking_anomalous_above_normal():
    """An outlier's contributions should highlight the features that make it deviant."""
    samples = [_flat(i, float(1 + i)) for i in range(20)]
    outlier_features = {
        "event_frequency": 1.0,
        "frequency_change": 0.0,
        "mean_interval_days": 30.0,
        "min_interval_days": 14.0,
        "temporal_cluster_count": 8.0,
        "longitudinal_deviation_abs": 7.5,
        "source_diversity": 6.0,
        "corroboration_count": 6.0,
        "relationship_degree": 12.0,
        "relationship_diversity": 6.0,
    }
    outlier = (uuid.uuid4(), outlier_features)
    samples.append(outlier)
    outcomes, meta = detect_anomalies(samples, CFG)
    by_id = {o.subject_id: o for o in outcomes}
    outlier_outcome = by_id[outlier[0]]
    assert 0.0 <= outlier_outcome.normalized_score <= 100.0
    assert meta["population"] == 21
    contributions = {c.feature_id: c for c in outlier_outcome.contributions}
    assert abs(sum(c.contribution for c in outlier_outcome.contributions) - 1.0) < 1e-4
    deviant_features = {"corroboration_count", "source_diversity", "relationship_degree",
                        "relationship_diversity", "temporal_cluster_count",
                        "longitudinal_deviation_abs"}
    top_features = {c.feature_id for c in outlier_outcome.contributions[:3]}
    assert top_features & deviant_features, (
        f"Top contributions should include deviant features, got {top_features}"
    )


def test_single_subject_is_neutral():
    samples = [_flat(0, 4.0)]
    outcomes, _ = detect_anomalies(samples, CFG)
    assert len(outcomes) == 1
    assert outcomes[0].normalized_score == 50.0
    assert not outcomes[0].is_anomaly


def test_contributions_reference_actual_features():
    outlier = (
        uuid.uuid4(),
        {
            **_flat(0, 1.0)[1],
            "corroboration_count": 6.0,
        },
    )
    samples = [_flat(i, float(1 + i)) for i in range(5)] + [outlier]
    outcomes, _ = detect_anomalies(samples, CFG)
    target = next(o for o in outcomes if o.subject_id == outlier[0])
    assert target.contributions
    contributions = list(target.contributions)
    top = contributions[0]
    assert top.feature_id == "corroboration_count"
    assert top.actual_value == 6.0
    assert top.contribution > 0
    total = sum(c.contribution for c in contributions)
    assert abs(total - 1.0) < 1e-6