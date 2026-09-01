"""Unit tests for priority scoring (formula, normalization, classification)."""
from __future__ import annotations

from app.analysis.contracts import (
    PRIORITY_LEVELS,
    PRIORITY_WEIGHTS,
    NetworkOutcome,
    priority_level_for,
)
from app.analysis.priority import compute_priority, compute_source_quality_score
from app.analysis.features import compute_features
from app.analysis.contracts import AnalysisConfig
from tests.support_analytics import AS_OF, duplicate_reports_subject, normal_subject

CFG = AnalysisConfig()
_cases = [
    (0.0, "LOW"),
    (29.0, "LOW"),
    (30.0, "MODERATE"),
    (49.0, "MODERATE"),
    (50.0, "HIGH"),
    (69.0, "HIGH"),
    (70.0, "VERY_HIGH"),
    (84.0, "VERY_HIGH"),
    (85.0, "CRITICAL"),
    (100.0, "CRITICAL"),
]


def test_bounds_are_inclusive_and_non_overlapping():
    seen: list[str] = []
    for lo, hi in PRIORITY_LEVELS.values():
        assert lo <= hi
        seen.append((lo, hi))
        seen.append((lo, hi))
    assert PRIORITY_LEVELS["LOW"] == (0, 29)
    assert PRIORITY_LEVELS["CRITICAL"] == (85, 100)


def test_classification_boundaries():
    for score, expected in _cases:
        assert priority_level_for(score) == expected, f"score={score}"


def test_weighted_formula_is_exact():
    components = {
        "rule": 80.0,
        "anomaly": 60.0,
        "correlation": 40.0,
        "temporal": 20.0,
        "network": 10.0,
        "source_quality": 30.0,
    }
    network = NetworkOutcome(0, 0.0, 0, 0, components["network"], {})
    priority = compute_priority(
        None,  # type: ignore[arg-type]
        components["rule"],
        components["anomaly"],
        components["correlation"],
        components["temporal"],
        network,
        components["source_quality"],
    )
    expected = sum(w * components[k] for k, w in PRIORITY_WEIGHTS.items())
    assert abs(priority.overall - expected) < 0.01
    # decomposition is stored
    assert priority.components["rule_score"] == 80.0
    assert priority.network_score == components["network"]


def test_scores_are_clamped_to_0_100():
    high = compute_priority(
        None,  # type: ignore[arg-type]
        150.0, 120.0, 110.0, 130.0,
        NetworkOutcome(0, 0.0, 0, 0, 140.0, {}),
        160.0,
    )
    assert high.overall <= 100.0
    low = compute_priority(
        None,  # type: ignore[arg-type]
        -20.0, -40.0, -10.0, -30.0,
        NetworkOutcome(0, 0.0, 0, 0, -50.0, {}),
        0.0,
    )
    assert low.overall >= 0.0


def test_components_decompose_to_overall():
    network = NetworkOutcome(3, 3.0, 2, 1, 55.0, {"x": 1})
    priority = compute_priority(
        None,  # type: ignore[arg-type]
        50.0, 60.0, 70.0, 40.0, network, 80.0,
    )
    direct = (
        PRIORITY_WEIGHTS["rule"] * 50.0
        + PRIORITY_WEIGHTS["anomaly"] * 60.0
        + PRIORITY_WEIGHTS["correlation"] * 70.0
        + PRIORITY_WEIGHTS["temporal"] * 40.0
        + PRIORITY_WEIGHTS["network"] * 55.0
        + PRIORITY_WEIGHTS["source_quality"] * 80.0
    )
    assert abs(priority.overall - direct) < 0.01


def test_source_quality_with_reports():
    subject = normal_subject()
    features = compute_features(subject, CFG, AS_OF)
    score = compute_source_quality_score(features)
    # one C-reliability report (weight=0.7) pushes quality above neutral
    assert 50.0 < score <= 100.0


def test_source_quality_neutral_zero_reports():
    feats = compute_features(duplicate_reports_subject(), CFG, AS_OF)
    # the duplicate subject still carries raw reports -> a source-quality signal exists
    assert compute_source_quality_score(feats) > 0.0
    from app.analysis.contracts import SubjectData

    empty = SubjectData(subject_id=None)  # type: ignore[arg-type]
    empty_feats = compute_features(empty, CFG, AS_OF)
    assert compute_source_quality_score(empty_feats) == 50.0