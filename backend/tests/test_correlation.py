"""Unit tests for temporal and cross-source correlation, incl. deduplication."""
from __future__ import annotations

from app.analysis.contracts import AnalysisConfig
from app.analysis.correlation import cross_source_correlation, temporal_correlation
from tests.support_analytics import (
    AS_OF,
    duplicate_reports_subject,
    make_signal,
    make_subject,
    multi_source_subject,
    normal_subject,
)

CFG = AnalysisConfig()


def test_temporal_rejects_events_outside_window():
    inside = make_subject([
        make_signal(category="TESTING", days_ago=30, source_category="NADO-TEST", weight=1.0),
        make_signal(category="REPORT", days_ago=20, source_category="CONFIDENTIAL", info_category="X", weight=0.7),
    ])
    outside = make_subject([
        make_signal(category="TESTING", days_ago=400, source_category="NADO-TEST", weight=1.0),
        make_signal(category="REPORT", days_ago=200, source_category="CONFIDENTIAL", info_category="X", weight=0.7),
    ])
    assert temporal_correlation(inside, CFG, AS_OF).signal_count == 2
    assert temporal_correlation(outside, CFG, AS_OF).signal_count == 0


def test_temporal_score_grows_with_categories():
    one = make_subject([make_signal(category="TESTING", days_ago=5, source_category="A", weight=1.0)])
    many = make_subject([
        make_signal(category="TESTING", days_ago=30, source_category="A", weight=1.0),
        make_signal(category="WHEREABOUTS", days_ago=20, source_category="B", weight=1.0),
        make_signal(category="TRAVEL", days_ago=10, source_category="C", weight=1.0),
        make_signal(category="REPORT", days_ago=5, source_category="D", info_category="X", weight=0.7),
    ])
    assert temporal_correlation(many, CFG, AS_OF).score > temporal_correlation(one, CFG, AS_OF).score


def test_rows_are_windowed_and_scored_zero():
    empty = make_subject()
    out = temporal_correlation(empty, CFG, AS_OF)
    assert out.score == 0.0 and out.signal_count == 0


def test_cross_source_dedupes_duplicate_reports():
    single = cross_source_correlation(duplicate_reports_subject(), CFG, AS_OF)
    # 3 identical reports from one source become one deduplicated report.
    assert single.signal_count == 1
    assert single.category_count == 1


def test_cross_source_counts_independent_categories():
    multi = cross_source_correlation(multi_source_subject(), CFG, AS_OF)
    assert multi.category_count >= 3
    assert multi.signal_count >= 3


def test_cross_source_independent_beats_duplicates():
    a = cross_source_correlation(duplicate_reports_subject(), CFG, AS_OF).score
    b = cross_source_correlation(multi_source_subject(), CFG, AS_OF).score
    assert b > a


def test_explicit_duplicate_flag_skipped():
    subj = make_subject([
        make_signal(category="REPORT", days_ago=5, source_category="CONFIDENTIAL", info_category="X", weight=0.9, is_duplicate=True),
    ])
    out = cross_source_correlation(subj, CFG, AS_OF)
    assert out.signal_count == 0
    assert out.score == 0.0


def test_normal_subject_no_corroboration():
    out = cross_source_correlation(normal_subject(), CFG, AS_OF)
    assert out.score < cross_source_correlation(multi_source_subject(), CFG, AS_OF).score