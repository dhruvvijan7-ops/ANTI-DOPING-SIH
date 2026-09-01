"""Versioned feature computation (pipeline stage 5).

Every feature has an identifier, a version, a description, a deterministic
calculation and the explicit source fields it uses. All calculations are pure
functions of :class:`app.analysis.contracts.SubjectData` plus an ``as_of`` reference
date, so results are reproducible for identical inputs.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.analysis.contracts import (
    AnalysisConfig,
    FeatureValue,
    Signal,
    SubjectData,
)

# Admiralty reliability letters mapped to numeric weights (D-010, source code A..F).
RELIABILITY_WEIGHTS = {"A": 1.0, "B": 0.85, "C": 0.7, "D": 0.5, "E": 0.3, "F": 0.1}

FEATURE_VERSION = 2
_BURST_GAP_DAYS = 7  # signals separated by <= this gap belong to one temporal burst
_HIGH_DEVIATION = 2.5  # |baseline_deviation| at/above this counts as a strong deviation


def _recent(signals: list[Signal], as_of: date, days: int) -> list[Signal]:
    lo = as_of - timedelta(days=days)
    return [s for s in signals if lo <= s.occurred_on <= as_of]


def _prior(signals: list[Signal], as_of: date, days: int) -> list[Signal]:
    hi = as_of - timedelta(days=days)
    lo = hi - timedelta(days=days)
    return [s for s in signals if lo <= s.occurred_on < hi]


def _sorted(signals: list[Signal]) -> list[Signal]:
    return sorted(signals, key=lambda s: s.occurred_on)


# --------------------------------------------------------------------------- features


def event_frequency(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    return float(len(_recent(subject.signals, as_of, cfg.recent_window_days)))


def frequency_change(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    """Directional rate change between the recent and the preceding window, in [-1, 1].

    0 = no change; + = acceleration; - = deceleration (no recent activity).
    """
    recent = len(_recent(subject.signals, as_of, cfg.recent_window_days))
    prior = len(_prior(subject.signals, as_of, cfg.recent_window_days))
    return round((recent - prior) / max(1.0, float(recent + prior)), 4)


def mean_interval_days(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    recent = _recent(subject.signals, as_of, cfg.recent_window_days)
    seq = _sorted(recent)
    gaps = [
        (b.occurred_on - a.occurred_on).days
        for a, b in zip(seq, seq[1:])
    ]
    if not gaps:
        return 0.0
    return round(sum(gaps) / len(gaps), 2)


def min_interval_days(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    recent = _recent(subject.signals, as_of, cfg.recent_window_days)
    seq = _sorted(recent)
    gaps = [
        (b.occurred_on - a.occurred_on).days
        for a, b in zip(seq, seq[1:])
    ]
    return float(min(gaps)) if gaps else 0.0


def temporal_cluster_count(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    """Number of temporal bursts (chains of >=2 signals with gaps <= 7 days)."""
    seq = _sorted(_recent(subject.signals, as_of, cfg.recent_window_days))
    clusters: list[list[Signal]] = []
    current: list[Signal] = []
    for sig in seq:
        if current and (sig.occurred_on - current[-1].occurred_on).days <= _BURST_GAP_DAYS:
            current.append(sig)
        else:
            if len(current) >= 2:
                clusters.append(current)
            current = [sig]
    if len(current) >= 2:
        clusters.append(current)
    return float(len(clusters))


def longitudinal_deviation_abs(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    bios = [s for s in _recent(subject.signals, as_of, cfg.recent_window_days) if s.category == "BIOLOGICAL"]
    devs = [
        abs(s.value)
        for s in bios
        if s.value is not None
    ]
    if not devs:
        return 0.0
    return round(sum(devs) / len(devs), 4)


def bio_high_deviation_count(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    bios = [s for s in _recent(subject.signals, as_of, cfg.recent_window_days) if s.category == "BIOLOGICAL"]
    return float(sum(1 for s in bios if s.value is not None and abs(s.value) >= _HIGH_DEVIATION))


def source_diversity(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    categories = {
        s.source_category for s in _recent(subject.signals, as_of, cfg.recent_window_days)
        if s.source_category and s.source_category != "UNKNOWN"
    }
    return float(len(categories))


def corroboration_count(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    """Max number of independent source categories reporting the same info_category."""
    by_info: dict[str, set] = defaultdict(set)
    for s in _recent(subject.signals, as_of, cfg.recent_window_days):
        if s.category != "REPORT" or not s.info_category:
            continue
        by_info[s.info_category].add(s.source_category)
    if not by_info:
        return 0.0
    return float(max(len(cats) for cats in by_info.values()))


def report_volume(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    return float(
        sum(1 for s in _recent(subject.signals, as_of, cfg.recent_window_days) if s.category == "REPORT")
    )


def report_reliability_weighted(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    reports = [
        s.weight for s in _recent(subject.signals, as_of, cfg.recent_window_days)
        if s.category == "REPORT"
    ]
    if not reports:
        return 0.0
    return round(sum(reports) / len(reports), 4)


def event_count_total(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    return float(len(subject.signals))


def relationship_degree(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    return float(len(subject.relationships))


def connected_entity_count(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    others = {
        e.other_subject_id
        for e in subject.relationships
        if e.other_subject_id is not None
    }
    return float(len(others))


def relationship_diversity(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    types = {e.edge_type for e in subject.relationships}
    return float(len(types))


def weighted_degree(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    return round(sum(e.weight for e in subject.relationships), 4)


def connected_alert_count(subject: SubjectData, cfg: AnalysisConfig, as_of: date) -> float:
    """Static proxy for 'connected alerts' (feeds the ML feature matrix).

    The dynamic connected-priority count is computed during the network stage using
    the run's own scores; here we count connected entities weighted 0..1.
    """
    return min(1.0, connected_entity_count(subject, cfg, as_of) / 20.0)


# Feature registry: identifier -> {version, description, source_fields, func}
FEATURE_DEFS: dict[str, dict] = {
    "event_frequency": {
        "version": FEATURE_VERSION,
        "description": "Number of events/reports received for the subject in the recent window (event frequency).",
        "source_fields": ["signals.[occurred_on] within recent_window_days"],
        "func": event_frequency,
    },
    "frequency_change": {
        "version": FEATURE_VERSION,
        "description": "Directional rate change between recent and preceding windows in [-1, 1] (acceleration proxy).",
        "source_fields": ["signals.[occurred_on] recent vs prior window"],
        "func": frequency_change,
    },
    "mean_interval_days": {
        "version": FEATURE_VERSION,
        "description": "Mean interval in days between consecutive signals in the recent window (time intervals).",
        "source_fields": ["signals.[occurred_on] sorted gaps"],
        "func": mean_interval_days,
    },
    "min_interval_days": {
        "version": FEATURE_VERSION,
        "description": "Minimum interval in days between consecutive recent signals (tightest time interval).",
        "source_fields": ["signals.[occurred_on] sorted gaps"],
        "func": min_interval_days,
    },
    "temporal_cluster_count": {
        "version": FEATURE_VERSION,
        "description": "Number of temporal bursts (>=2 signals with inter-signal gap <=7 days) (temporal clustering).",
        "source_fields": ["signals.[occurred_on]"],
        "func": temporal_cluster_count,
    },
    "longitudinal_deviation_abs": {
        "version": FEATURE_VERSION,
        "description": "Mean absolute baseline deviation of recent biological observations (longitudinal deviation).",
        "source_fields": ["BIOLOGICAL signals.[value=baseline_deviation]"],
        "func": longitudinal_deviation_abs,
    },
    "bio_high_deviation_count": {
        "version": FEATURE_VERSION,
        "description": "Count of recent biological observations with |baseline_deviation| >= 2.5.",
        "source_fields": ["BIOLOGICAL signals.[value=baseline_deviation]"],
        "func": bio_high_deviation_count,
    },
    "source_diversity": {
        "version": FEATURE_VERSION,
        "description": "Distinct independent source categories providing recent signals (source diversity).",
        "source_fields": ["signals.[source_category]"],
        "func": source_diversity,
    },
    "corroboration_count": {
        "version": FEATURE_VERSION,
        "description": "Max distinct source categories corroborating one info_category via reports (corroboration).",
        "source_fields": ["REPORT signals.[info_category, source_category]"],
        "func": corroboration_count,
    },
    "report_volume": {
        "version": FEATURE_VERSION,
        "description": "Count of recent intelligence reports linked to the subject.",
        "source_fields": ["REPORT signals"],
        "func": report_volume,
    },
    "report_reliability_weighted": {
        "version": FEATURE_VERSION,
        "description": "Mean Admiralty reliability weight (A=1.0..F=0.1) of recent reports.",
        "source_fields": ["REPORT signals.[weight]"],
        "func": report_reliability_weighted,
    },
    "event_count_total": {
        "version": FEATURE_VERSION,
        "description": "Total number of signals across all time for the subject.",
        "source_fields": ["signals"],
        "func": event_count_total,
    },
    "relationship_degree": {
        "version": FEATURE_VERSION,
        "description": "Number of recorded relationships touching the subject (relationship degree).",
        "source_fields": ["relationships"],
        "func": relationship_degree,
    },
    "connected_entity_count": {
        "version": FEATURE_VERSION,
        "description": "Distinct other entities directly connected to the subject.",
        "source_fields": ["relationships.[other_subject_id]"],
        "func": connected_entity_count,
    },
    "relationship_diversity": {
        "version": FEATURE_VERSION,
        "description": "Distinct relationship types recorded for the subject (relationship diversity).",
        "source_fields": ["relationships.[edge_type]"],
        "func": relationship_diversity,
    },
    "weighted_degree": {
        "version": FEATURE_VERSION,
        "description": "Sum of relationship confidence weights (weighted degree).",
        "source_fields": ["relationships.[weight]"],
        "func": weighted_degree,
    },
    "connected_alert_count": {
        "version": FEATURE_VERSION,
        "description": "Normalized count of connected entities (proxy for network-relevant alert exposure).",
        "source_fields": ["relationships.[other_subject_id]"],
        "func": connected_alert_count,
    },
}


def feature_catalog() -> list[dict]:
    """Catalog rows persisted as FeatureVersion entries."""
    return [
        {
            "identifier": ident,
            "version": meta["version"],
            "description": meta["description"],
            "source_fields_json": list(meta["source_fields"]),
        }
        for ident, meta in sorted(FEATURE_DEFS.items())
    ]


def compute_features(
    subject: SubjectData,
    cfg: AnalysisConfig,
    as_of: date,
) -> dict[str, FeatureValue]:
    """Compute every registered feature for one subject. Pure and deterministic."""
    result: dict[str, FeatureValue] = {}
    for identifier, meta in FEATURE_DEFS.items():
        value = float(meta["func"](subject, cfg, as_of))
        result[identifier] = FeatureValue(
            identifier=identifier,
            version=meta["version"],
            value=round(float(value), 6),
            source_fields={
                field_name: None for field_name in meta["source_fields"]
            },
            description=meta["description"],
        )
    return result


def reliability_weight(code: str | None) -> float:
    return RELIABILITY_WEIGHTS.get(code or "", 0.5)