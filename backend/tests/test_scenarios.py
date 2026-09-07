"""Scenario validation: end-to-end pure pipeline over structured scenarios.

These validate the engineering requirements: a network scenario scores above a
normal scenario, a multiple-independent-source scenario scores above a normal
scenario, and a strong single-signal anomaly without corroboration (false positive)
stays reviewable -- never reaching CRITICAL and never being treated as guilt.
"""
from __future__ import annotations

import uuid
from datetime import date

from app.analysis.anomaly import detect_anomalies
from app.analysis.contracts import AnalysisConfig, PRIORITY_LEVELS
from app.analysis.correlation import cross_source_correlation, temporal_correlation
from app.analysis.features import compute_features
from app.analysis.network import network_relevance
from app.analysis.priority import compute_priority, compute_source_quality_score
from app.analysis.rules import evaluate_rules
from app.analysis.contracts import PriorityOutcome
from tests.support_analytics import (
    multi_source_subject,
    network_subject,
    normal_subject,
    single_anomaly_subject,
)

CFG = AnalysisConfig()
AS_OF = date(2026, 8, 31)


def _id() -> uuid.UUID:
    return uuid.uuid4()


NORMAL = [_id() for _ in range(6)]
NETWORK = _id()
MULTI = _id()
FALSE_POSITIVE = _id()

POPULATION = [
    normal_subject(subject_id=NORMAL[0]),
    network_subject(subject_id=NETWORK),
    multi_source_subject(subject_id=MULTI),
    single_anomaly_subject(subject_id=FALSE_POSITIVE),
    normal_subject(subject_id=NORMAL[1]),
    normal_subject(subject_id=NORMAL[2]),
    normal_subject(subject_id=NORMAL[3]),
    normal_subject(subject_id=NORMAL[4]),
    normal_subject(subject_id=NORMAL[5]),
]


def pipeline_population(subjects: list) -> dict[uuid.UUID, PriorityOutcome]:
    """Run the full scoring pipeline in memory (mirrors the runner's math)."""
    results: dict[uuid.UUID, PriorityOutcome] = {}
    features = {s.subject_id: compute_features(s, CFG, AS_OF) for s in subjects}
    rule_scores = {
        s.subject_id: evaluate_rules(s, features[s.subject_id], CFG, AS_OF)[1] for s in subjects
    }
    samples = [
        (
            s.subject_id,
            {k: v.value for k, v in features[s.subject_id].items()},
        )
        for s in subjects
    ]
    # Match the runner: the anomaly matrix excludes graph features (network stage).
    from app.analysis.features import GRAPH_FEATURE_IDS

    samples = [
        (sid, {k: v for k, v in feats.items() if k not in GRAPH_FEATURE_IDS})
        for sid, feats in samples
    ]
    anomaly_outcomes = {o.subject_id: o for o in detect_anomalies(samples, CFG)[0]}
    temporal = {s.subject_id: temporal_correlation(s, CFG, AS_OF) for s in subjects}
    cross = {s.subject_id: cross_source_correlation(s, CFG, AS_OF) for s in subjects}

    provisional: dict[uuid.UUID, float] = {}
    for s in subjects:
        net = network_relevance(s, CFG, AS_OF, priorities={})
        priority = compute_priority(
            s.subject_id,
            rule_scores[s.subject_id],
            anomaly_outcomes[s.subject_id].normalized_score,
            cross[s.subject_id].score,
            temporal[s.subject_id].score,
            net,
            compute_source_quality_score(features[s.subject_id]),
        )
        provisional[s.subject_id] = priority.overall
    for s in subjects:
        net = network_relevance(s, CFG, AS_OF, priorities=provisional)
        priority = compute_priority(
            s.subject_id,
            rule_scores[s.subject_id],
            anomaly_outcomes[s.subject_id].normalized_score,
            cross[s.subject_id].score,
            temporal[s.subject_id].score,
            net,
            compute_source_quality_score(features[s.subject_id]),
        )
        results[s.subject_id] = priority
    return results


def test_network_scenario_outranks_normal():
    results = pipeline_population(POPULATION)
    normal_avg = sum(results[sid].overall for sid in NORMAL) / len(NORMAL)
    assert results[NETWORK].overall > normal_avg


def test_multi_source_scenario_outranks_normal():
    results = pipeline_population(POPULATION)
    normal_avg = sum(results[sid].overall for sid in NORMAL) / len(NORMAL)
    assert results[MULTI].overall > normal_avg


def test_false_positive_stays_reviewable():
    results = pipeline_population(POPULATION)
    priority = results[FALSE_POSITIVE]
    assert priority.overall < 70.0
    assert priority.level in {"LOW", "MODERATE", "HIGH"}
    assert priority.level != "CRITICAL"


def test_normal_scenario_stays_low():
    results = pipeline_population(POPULATION)
    for sid in NORMAL:
        assert results[sid].level in {"LOW", "MODERATE"}
        assert results[sid].overall < 50.0


def test_all_levels_are_valid():
    results = pipeline_population(POPULATION)
    for priority in results.values():
        assert priority.level in PRIORITY_LEVELS
        assert 0.0 <= priority.overall <= 100.0