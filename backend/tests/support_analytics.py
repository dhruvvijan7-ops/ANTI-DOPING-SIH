"""Deterministic builders for analytics tests (pure pipeline + DB-backed)."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.analysis.contracts import RelationshipEdge, Signal, SubjectData

AS_OF = date(2026, 8, 31)


def make_signal(
    category: str = "REPORT",
    days_ago: int = 30,
    source_category: str = "CONFIDENTIAL",
    info_category: str | None = None,
    weight: float = 0.85,
    dedupe_key: str | None = None,
    is_duplicate: bool = False,
    status: str | None = None,
    value: float | None = None,
    reliability: str | None = "B",
    signal_id: uuid.UUID | None = None,
) -> Signal:
    return Signal(
        signal_id=signal_id or uuid.uuid4(),
        category=category,
        occurred_on=AS_OF - timedelta(days=days_ago),
        source_id=None,
        source_category=source_category,
        info_category=info_category,
        value=value,
        weight=weight,
        dedupe_key=dedupe_key,
        raw_ref={
            "reliability": reliability,
            "status": status,
            "is_duplicate": is_duplicate,
            "info_category": info_category,
        },
    )


def make_subject(
    signals: list[Signal] | None = None,
    relationships: list[RelationshipEdge] | None = None,
    subject_id: uuid.UUID | None = None,
) -> SubjectData:
    return SubjectData(
        subject_id=subject_id or uuid.uuid4(),
        subject_type="ATHLETE",
        signals=signals or [],
        relationships=relationships or [],
    )


def make_edge(
    edge_type: str = "TEAM_MEMBER",
    weight: float = 1.0,
    other_id: uuid.UUID | None = None,
    direction: str = "OUT",
) -> RelationshipEdge:
    return RelationshipEdge(
        edge_type=edge_type,
        direction=direction,
        weight=weight,
        other_subject_type="ATHLETE",
        other_subject_id=other_id or uuid.uuid4(),
    )


def normal_subject(subject_id: uuid.UUID | None = None) -> SubjectData:
    """Evenly spread, low-volume, single-source subject (should stay LOW)."""
    sigs = [
        make_signal(category="TESTING", days_ago=150, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=140, source_category="NADO-TEST", weight=1.0),
        make_signal(category="REPORT", days_ago=60, source_category="CONFIDENTIAL", info_category="GENERAL", weight=0.7),
    ]
    return make_subject(sigs, subject_id=subject_id)


def network_subject(subject_id: uuid.UUID | None = None) -> SubjectData:
    """Subject embedded in a dense relational network (network relevance driver).

    Has the same signal profile as a normal subject, plus 5 relationship edges,
    so the network component is the differentiator.
    """
    rels = [
        make_edge("TEAM_MEMBER", 1.0),
        make_edge("TRAINING_GROUP", 1.0),
        make_edge("PHYSICIAN_PATIENT", 0.9),
        make_edge("FAMILY", 0.8),
        make_edge("AGENT_RELATION", 0.7),
    ]
    sigs = [
        make_signal(category="TESTING", days_ago=150, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=140, source_category="NADO-TEST", weight=1.0),
        make_signal(category="REPORT", days_ago=60, source_category="CONFIDENTIAL", info_category="GENERAL", weight=0.7),
    ]
    return make_subject(sigs, rels, subject_id=subject_id)


def multi_source_subject(subject_id: uuid.UUID | None = None) -> SubjectData:
    """Independently corroborated claims from several source categories."""
    sigs = [
        make_signal(category="REPORT", days_ago=10, source_category="CONFIDENTIAL", info_category="DOPING", weight=0.9, reliability="B"),
        make_signal(category="REPORT", days_ago=9, source_category="OSINT", info_category="DOPING", weight=0.7, reliability="C"),
        make_signal(category="REPORT", days_ago=8, source_category="LEO", info_category="DOPING", weight=0.8, reliability="C"),
        make_signal(category="TESTING", days_ago=20, source_category="NADO-TEST", weight=1.0),
        make_signal(category="WHEREABOUTS", days_ago=15, source_category="ADAMS", weight=1.0),
        make_signal(category="TRAVEL", days_ago=5, source_category="BORDER", weight=1.0),
    ]
    return make_subject(sigs, subject_id=subject_id)


def single_anomaly_subject(
    subject_id: uuid.UUID | None = None,
    deviations: list[float] | None = None,
) -> SubjectData:
    """Strong single-signal anomaly with NO corroboration (false-positive scenario)."""
    sigs = [
        make_signal(category="BIOLOGICAL", days_ago=30, value=3.2, weight=1.0),
        make_signal(category="BIOLOGICAL", days_ago=28, value=3.0, weight=1.0),
        make_signal(category="BIOLOGICAL", days_ago=26, value=2.9, weight=1.0),
        make_signal(category="TESTING", days_ago=25, source_category="NADO-TEST", weight=1.0),
    ]
    return make_subject(sigs, subject_id=subject_id)


def duplicate_reports_subject(subject_id: uuid.UUID | None = None) -> SubjectData:
    """A single claim shoveled in as many 'reports' (must NOT inflate cross-source)."""
    reports = [
        make_signal(category="REPORT", days_ago=10, source_category="CONFIDENTIAL", info_category="DOPING", weight=0.9),
        make_signal(category="REPORT", days_ago=9, source_category="CONFIDENTIAL", info_category="DOPING", weight=0.9),
        make_signal(category="REPORT", days_ago=8, source_category="CONFIDENTIAL", info_category="DOPING", weight=0.9),
    ]
    return make_subject(reports, subject_id=subject_id)