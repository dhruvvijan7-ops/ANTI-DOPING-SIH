"""Deterministic rule engine (pipeline stage 6).

Rules live in a registry, are independently enabled/disabled, and are never embedded
in endpoints. A rule fires only from actual computed fields; every trigger records
which conditions held and a human-readable expression.
"""
from __future__ import annotations

from datetime import date

from app.analysis.contracts import (
    AnalysisConfig,
    FeatureValue,
    RuleOutcome,
    SubjectData,
)
from app.analysis.features import reliability_weight

RULE_VERSION = 1

# Severity labels and their numeric weight for aggregate rule scoring.
SEVERITY_VALUE = {"LOW": 0.25, "MODERATE": 0.5, "HIGH": 0.75, "CRITICAL": 1.0}

WHEREABOUTS_FAILURE_STATUSES = ("MISSED", "FAILURE")


def _f(features: dict[str, FeatureValue], key: str) -> float:
    fv = features.get(key)
    return fv.value if fv else 0.0


def _report_volume(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    volume = int(_f(features, "report_volume"))
    cond = volume >= 3
    return cond, [f"report_volume={volume} >= 3"], {"report_volume": volume}


def _corroboration(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    corr = int(_f(features, "corroboration_count"))
    cond = corr >= 2
    return cond, [f"corroboration_count={corr} >= 2"], {"corroboration_count": corr}


def _temporal_burst(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    clusters = int(_f(features, "temporal_cluster_count"))
    cond = clusters >= 2
    return cond, [f"temporal_cluster_count={clusters} >= 2"], {"temporal_cluster_count": clusters}


def _high_reliability(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    reliability = _f(features, "report_reliability_weighted")
    cond = reliability >= 0.85
    return cond, [f"report_reliability_weighted={reliability} >= 0.85"], {"reliability_weighted": reliability}


def _biological_deviation(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    high = int(_f(features, "bio_high_deviation_count"))
    cond = high >= 1
    return cond, [f"bio_high_deviation_count={high} >= 1"], {"high_deviation_count": high}


def _network_density(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    degree = int(_f(features, "relationship_degree"))
    cond = degree >= 3
    return cond, [f"relationship_degree={degree} >= 3"], {"degree": degree}


def _multi_category(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> tuple[bool, list[str], dict]:
    from datetime import timedelta

    lo = as_of - timedelta(days=cfg.recent_window_days)
    cats = {
        s.category
        for s in subject.signals
        if lo <= s.occurred_on <= as_of
    }
    cond = len(cats) >= 4
    return cond, [f"distinct_recent_categories={len(cats)} >= 4"], {"categories": sorted(cats)}


def _whereabouts_anomaly(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> tuple[bool, list[str], dict]:
    from datetime import timedelta

    lo = as_of - timedelta(days=cfg.recent_window_days)
    failures = [
        s for s in subject.signals
        if s.category == "WHEREABOUTS" and lo <= s.occurred_on <= as_of
        and s.raw_ref.get("status") in WHEREABOUTS_FAILURE_STATUSES
    ]
    cond = len(failures) >= 1
    return cond, [f"whereabouts_failures={len(failures)} >= 1"], {"failure_signals": [str(s.signal_id) for s in failures]}


def _interval_density(subject: SubjectData, features: dict[str, FeatureValue]) -> tuple[bool, list[str], dict]:
    mini = _f(features, "min_interval_days")
    count = int(_f(features, "event_frequency"))
    cond = mini <= 2.0 and count >= 5
    return cond, [f"min_interval_days={mini} <= 2", f"event_frequency={count} >= 5"], {
        "min_interval_days": mini,
        "event_frequency": count,
    }


# Registry. `check` is called as check(subject, features, cfg, as_of) -> (triggered, conditions, detail)
_SPECIAL_ARGS = {"_multi_category", "_whereabouts_anomaly"}

RULES: list[dict] = [
    {
        "rule_id": "RULES-001",
        "version": RULE_VERSION,
        "name": "High report volume",
        "description": "Three or more intelligence reports were received for the subject in the recent window.",
        "severity": "LOW",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "report_volume", "threshold": 3, "op": ">="},
        "expression": "report_volume >= 3",
        "check": _report_volume,
    },
    {
        "rule_id": "RULES-002",
        "version": RULE_VERSION,
        "name": "Independent corroboration",
        "description": "At least two independent source categories corroborate the same report claim.",
        "severity": "MODERATE",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "corroboration_count", "threshold": 2, "op": ">="},
        "expression": "corroboration_count >= 2",
        "check": _corroboration,
    },
    {
        "rule_id": "RULES-003",
        "version": RULE_VERSION,
        "name": "Temporal burst",
        "description": "Multiple signals cluster into two or more tight temporal bursts in the recent window.",
        "severity": "MODERATE",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "temporal_cluster_count", "threshold": 2, "op": ">="},
        "expression": "temporal_cluster_count >= 2",
        "check": _temporal_burst,
    },
    {
        "rule_id": "RULES-004",
        "version": RULE_VERSION,
        "name": "High-reliability reporting",
        "description": "Recent reports carry high Admiralty reliability (weight >= 0.85).",
        "severity": "LOW",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "report_reliability_weighted", "threshold": 0.85, "op": ">="},
        "expression": "report_reliability_weighted >= 0.85",
        "check": _high_reliability,
    },
    {
        "rule_id": "RULES-005",
        "version": RULE_VERSION,
        "name": "Biological deviation",
        "description": "At least one recent biological observation deviates >= 2.5 from its baseline.",
        "severity": "HIGH",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "bio_high_deviation_count", "threshold": 1, "op": ">="},
        "expression": "bio_high_deviation_count >= 1",
        "check": _biological_deviation,
    },
    {
        "rule_id": "RULES-006",
        "version": RULE_VERSION,
        "name": "Network density",
        "description": "The subject has three or more recorded relationships (dense local network).",
        "severity": "LOW",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "relationship_degree", "threshold": 3, "op": ">="},
        "expression": "relationship_degree >= 3",
        "check": _network_density,
    },
    {
        "rule_id": "RULES-007",
        "version": RULE_VERSION,
        "name": "Multi-category activity",
        "description": "Recent signals span four or more distinct signal categories.",
        "severity": "MODERATE",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "distinct_recent_categories", "threshold": 4, "op": ">="},
        "expression": "distinct recent signal categories >= 4",
        "check": _multi_category,
    },
    {
        "rule_id": "RULES-008",
        "version": RULE_VERSION,
        "name": "Whereabouts failure",
        "description": "A recent whereabouts record is a missed or failed filing.",
        "severity": "HIGH",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "whereabouts_failures", "threshold": 1, "op": ">="},
        "expression": "recent whereabouts status in (MISSED, FAILURE)",
        "check": _whereabouts_anomaly,
    },
    {
        "rule_id": "RULES-009",
        "version": RULE_VERSION,
        "name": "Interval density",
        "description": "Very tight signal intervals combined with high recent event frequency.",
        "severity": "MODERATE",
        "weight": 1.0,
        "is_enabled": True,
        "conditions_json": {"metric": "min_interval_days", "threshold": 2, "op": "<=", "and": {"event_frequency": 5}},
        "expression": "min_interval_days <= 2 AND event_frequency >= 5",
        "check": _interval_density,
    },
]


def rule_catalog() -> list[dict]:
    return [
        {
            "rule_id": r["rule_id"],
            "version": r["version"],
            "name": r["name"],
            "description": r["description"],
            "severity": r["severity"],
            "weight": r["weight"],
            "is_enabled": r["is_enabled"],
            "conditions_json": r["conditions_json"],
        }
        for r in RULES
    ]


def evaluate_rules(
    subject: SubjectData,
    features: dict[str, FeatureValue],
    cfg: AnalysisConfig,
    as_of: date,
) -> tuple[list[RuleOutcome], float]:
    """Evaluate all enabled rules for one subject. Returns (outcomes, rule_score).

    rule_score = weighted triggered severity / weighted severity of all enabled rules.
    """
    outcomes: list[RuleOutcome] = []
    total_weight = 0.0
    fired_weight = 0.0
    for rule in RULES:
        if not rule["is_enabled"]:
            continue
        check = rule["check"]
        _special = rule["rule_id"] in {"RULES-007", "RULES-008"}
        if _special:
            triggered, conditions, detail = check(subject, cfg, as_of)  # type: ignore[misc]
        else:
            triggered, conditions, detail = check(subject, features)  # type: ignore[misc]
        weight = SEVERITY_VALUE[rule["severity"]] * rule["weight"]
        total_weight += weight
        if triggered:
            fired_weight += weight
        outcomes.append(
            RuleOutcome(
                rule_id=rule["rule_id"],
                version=rule["version"],
                name=rule["name"],
                description=rule["description"],
                severity=rule["severity"],
                weight=rule["weight"],
                conditions_met=conditions if triggered else [],
                triggered=triggered,
                detail=detail,
                expression=rule["expression"],
            )
        )
    rule_score = round(fired_weight / total_weight * 100.0, 2) if total_weight > 0 else 0.0
    return outcomes, rule_score