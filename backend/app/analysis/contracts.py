"""Input/output contracts for the analytics pipeline.

Every stage consumes and produces one of these plain objects so the pipeline can be
reasoned about, unit-tested without a database, and executed from the API, the CLI or
the tests without divergence.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date


# Signal categories (stage 1 intake kinds available in the domain model).
SIGNAL_CATEGORIES = (
    "TESTING",
    "BIOLOGICAL",
    "WHEREABOUTS",
    "TRAVEL",
    "MEDICAL",
    "SUPPLEMENT",
    "REPORT",
)


@dataclass
class Signal:
    """A single raw record (event or intelligence report) linked to a subject."""

    signal_id: uuid.UUID
    category: str  # one of SIGNAL_CATEGORIES
    occurred_on: date
    source_id: uuid.UUID | None = None
    source_category: str = "UNKNOWN"  # independent source category (odometer diversity)
    info_category: str | None = None  # report info_category (corroboration subject)
    value: float | None = None
    weight: float = 1.0  # reliability-derived weight; 1.0 when unknown
    dedupe_key: str | None = None  # duplicate-report key; dedupe prevents score inflation
    raw_model: str | None = None  # domain table name (traceability back to raw record)
    raw_ref: dict = field(default_factory=dict)  # {field_name: actual value}


@dataclass
class RelationshipEdge:
    """One directed graph edge touching the subject."""

    edge_type: str
    direction: str  # OUT | IN | BIDIRECTIONAL
    weight: float = 1.0
    other_subject_type: str | None = None
    other_subject_id: uuid.UUID | None = None
    raw_ref: dict = field(default_factory=dict)


@dataclass
class SubjectData:
    """Everything the pipeline knows about one analytic subject (typically an athlete)."""

    subject_id: uuid.UUID
    subject_type: str = "ATHLETE"
    signals: list[Signal] = field(default_factory=list)
    relationships: list[RelationshipEdge] = field(default_factory=list)
    scenario_ref: str | None = None  # synthetic test scenario label (never set in prod)


@dataclass
class AnalysisConfig:
    """Deterministic engine configuration captured into the run record."""

    temporal_window_days: int = 45
    cross_source_window_days: int = 90
    rule_version: int = 1
    feature_version: int = 2
    alert_threshold: str = "HIGH"  # minimum priority level that produces an alert
    recent_window_days: int = 180  # "recent" horizon for frequency-change features
    isolation_forest: dict = field(
        default_factory=lambda: {
            "n_estimators": 200,
            "contamination": 0.05,
            "random_state": 42,
            "model_version": "1.0",
        }
    )

    def to_dict(self) -> dict:
        from dataclasses import asdict

        return asdict(self)


# Priority levels (spec stage 11 classification, section 24).
PRIORITY_LEVELS = {
    "LOW": (0, 29),
    "MODERATE": (30, 49),
    "HIGH": (50, 69),
    "VERY_HIGH": (70, 84),
    "CRITICAL": (85, 100),
}

# Priority components and their weights (0.25R + 0.20A + 0.20C + 0.15T + 0.10N + 0.10S).
PRIORITY_WEIGHTS = {
    "rule": 0.25,
    "anomaly": 0.20,
    "correlation": 0.20,
    "temporal": 0.15,
    "network": 0.10,
    "source_quality": 0.10,
}


def priority_level_for(score: float) -> str:
    """Classify a 0-100 score into the spec's five-level scheme."""
    for level, (lo, hi) in PRIORITY_LEVELS.items():
        if lo <= score <= hi:
            return level
    return "LOW"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def to_score(value: float, max_val: float) -> float:
    """Normalize a count/value against a ceiling into a 0-100 score."""
    if max_val <= 0:
        return 0.0
    return round(max(0.0, min(1.0, value / max_val)) * 100.0, 2)


@dataclass
class FeatureValue:
    identifier: str
    version: int
    value: float
    source_fields: dict
    description: str = ""


@dataclass
class RuleOutcome:
    rule_id: str
    version: int
    name: str
    description: str
    severity: str
    weight: float
    conditions_met: list[str]
    triggered: bool
    detail: dict
    expression: str


@dataclass
class CorrelatedCluster:
    category: str | None
    signal_ids: list[uuid.UUID]
    source_categories: list[str]


@dataclass
class CorrelationOutcome:
    correlation_type: str  # TEMPORAL | CROSS_SOURCE
    window_days: int
    score: float
    signal_count: int
    category_count: int
    signal_ids: list[uuid.UUID]
    clusters: list[CorrelatedCluster]
    description: str = ""


@dataclass
class NetworkOutcome:
    degree: int
    weighted_degree: float
    relationship_diversity: int
    connected_priority_count: int
    score: float
    detail: dict


@dataclass
class PriorityOutcome:
    subject_id: uuid.UUID
    overall: float
    level: str
    rule_score: float
    anomaly_score: float
    correlation_score: float
    temporal_score: float
    network_score: float
    source_quality_score: float
    explanation: str
    components: dict