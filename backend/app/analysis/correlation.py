"""Temporal and cross-source correlation (pipeline stages 8-9).

Temporal correlation looks for signals of different categories accumulating inside a
configurable rolling window (default 45 days). Cross-source correlation separates
independent source categories from duplicate information and counts corroborating
signals, explicitly preventing duplicate reports from inflating the score.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.analysis.contracts import (
    AnalysisConfig,
    CorrelatedCluster,
    CorrelationOutcome,
    Signal,
    SubjectData,
)


def _within(signals: list[Signal], as_of: date, days: int) -> list[Signal]:
    lo = as_of - timedelta(days=days)
    return [s for s in signals if lo <= s.occurred_on <= as_of]


def _reliability_weight(s: Signal) -> float:
    from app.analysis.features import reliability_weight

    return reliability_weight(s.raw_ref.get("reliability"))


def temporal_correlation(
    subject: SubjectData,
    cfg: AnalysisConfig,
    as_of: date,
) -> CorrelationOutcome:
    """Correlate signals accumulated inside the rolling temporal window."""
    window = cfg.temporal_window_days
    recent = _within(subject.signals, as_of, window)
    if not recent:
        return CorrelationOutcome(
            correlation_type="TEMPORAL",
            window_days=window,
            score=0.0,
            signal_count=0,
            category_count=0,
            signal_ids=[],
            clusters=[],
            description="No signals inside the temporal window.",
        )

    categories = sorted({s.category for s in recent})
    signal_ids = [s.signal_id for s in recent]
    cluster = CorrelatedCluster(
        category=None,
        signal_ids=signal_ids,
        source_categories=sorted({s.source_category for s in recent if s.source_category}),
    )
    # Deterministic scoring: categories span the 6 core categories; bursts add weight.
    burst_length = len(recent)
    score = min(
        100.0,
        round(len(categories) / 6.0 * 100.0, 2) + min(20.0, burst_length * 2.0),
    )
    return CorrelationOutcome(
        correlation_type="TEMPORAL",
        window_days=window,
        score=round(score, 2),
        signal_count=len(recent),
        category_count=len(categories),
        signal_ids=signal_ids,
        clusters=[cluster],
        description=(
            f"{len(recent)} signals across {len(categories)} categories "
            f"({', '.join(categories)}) inside the {window}-day window."
        ),
    )


def _dedupe_key(s: Signal) -> str:
    if s.dedupe_key:
        return f"key:{s.dedupe_key}"
    iso = s.occurred_on.isocalendar()
    week = f"{iso[0]}-{iso[1]}"
    return f"src:{s.source_category or 'UNKNOWN'}|cat:{s.info_category or 'NONE'}|week:{week}"


def cross_source_correlation(
    subject: SubjectData,
    cfg: AnalysisConfig,
    as_of: date,
) -> CorrelationOutcome:
    """Correlate reports across independent sources, counting duplicates once."""
    window = cfg.cross_source_window_days
    reports = [
        s
        for s in _within(subject.signals, as_of, window)
        if s.category == "REPORT"
    ]
    if not reports:
        return CorrelationOutcome(
            correlation_type="CROSS_SOURCE",
            window_days=window,
            score=0.0,
            signal_count=0,
            category_count=0,
            signal_ids=[],
            clusters=[],
            description="No reports inside the cross-source window.",
        )

    seen: set[str] = set()
    deduped: list[Signal] = []
    for s in reports:
        if s.raw_ref.get("is_duplicate"):
            continue  # explicitly flagged duplicate
        key = _dedupe_key(s)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)

    source_categories = sorted(
        {s.source_category for s in deduped if s.source_category and s.source_category != "UNKNOWN"}
    )
    by_info: dict[str, set] = {}
    for s in deduped:
        if s.info_category:
            by_info.setdefault(s.info_category, set()).add(s.source_category or "UNKNOWN")

    corroborated = {
        info: sorted(cats)
        for info, cats in by_info.items()
        if len(cats) >= 2
    }

    score = min(
        100.0,
        round(len(source_categories) * 25.0, 2) + min(30.0, len(corroborated) * 15.0),
    )
    signal_ids = [s.signal_id for s in deduped]
    clusters = [
        CorrelatedCluster(
            category=info,
            signal_ids=[s.signal_id for s in deduped if s.info_category == info],
            source_categories=cats,
        )
        for info, cats in corroborated.items()
    ]
    return CorrelationOutcome(
        correlation_type="CROSS_SOURCE",
        window_days=window,
        score=round(score, 2),
        signal_count=len(signal_ids),
        category_count=len(source_categories),
        signal_ids=signal_ids,
        clusters=clusters,
        description=(
            f"{len(signal_ids)} deduplicated reports from {len(source_categories)} "
            f"independent source categories ({len(reports)} raw reports counted once); "
            f"{len(corroborated)} corroborated claim(s)."
        ),
    )