"""Unit tests for the versioned feature engine (pure, no database)."""
from __future__ import annotations

from app.analysis.contracts import AnalysisConfig
from app.analysis.features import (
    FEATURE_DEFS,
    FEATURE_VERSION,
    compute_features,
    feature_catalog,
)
from tests.support_analytics import (
    AS_OF,
    duplicate_reports_subject,
    make_signal,
    make_subject,
    multi_source_subject,
    network_subject,
    normal_subject,
)

CFG = AnalysisConfig()


def _value(subject, key: str) -> float:
    return compute_features(subject, CFG, AS_OF)[key].value


def test_spec_five_names_present():
    keys = set(compute_features(normal_subject(), CFG, AS_OF).keys())
    for required in (
        "event_frequency",
        "frequency_change",
        "mean_interval_days",
        "longitudinal_deviation_abs",
        "temporal_cluster_count",
        "source_diversity",
        "corroboration_count",
        "relationship_degree",
        "connected_alert_count",
        "relationship_diversity",
    ):
        assert required in keys


def test_feature_catalog_is_versioned():
    catalog = feature_catalog()
    assert len(catalog) == len(FEATURE_DEFS)
    for row in catalog:
        assert row["version"] == FEATURE_VERSION
        assert row["description"]
        assert row["source_fields_json"]


def test_event_frequency_recent_window_only():
    subj = make_subject([
        make_signal(category="TESTING", days_ago=5, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=400, source_category="NADO-TEST", weight=1.0),
    ])
    assert _value(subj, "event_frequency") == 1.0
    assert _value(subj, "event_count_total") == 2.0


def test_frequency_change_acceleration():
    subj = make_subject([
        make_signal(category="TESTING", days_ago=170, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=160, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=5, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=2, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=1, source_category="NADO-TEST", weight=1.0),
    ])
    assert _value(subj, "frequency_change") > 0


def test_interval_features():
    subj = make_subject([
        make_signal(category="TESTING", days_ago=10, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=8, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=4, source_category="NADO-TEST", weight=1.0),
    ])
    assert _value(subj, "mean_interval_days") == 3.0
    assert _value(subj, "min_interval_days") == 2.0


def test_temporal_cluster_count_bursts():
    subj = make_subject([
        make_signal(category="TESTING", days_ago=30, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=28, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=26, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=5, source_category="NADO-TEST", weight=1.0),
        make_signal(category="TESTING", days_ago=2, source_category="NADO-TEST", weight=1.0),
    ])
    assert _value(subj, "temporal_cluster_count") == 2.0


def test_longitudinal_deviation_abs():
    subj = make_subject([
        make_signal(category="BIOLOGICAL", days_ago=20, value=3.0, weight=1.0),
        make_signal(category="BIOLOGICAL", days_ago=19, value=1.0, weight=1.0),
    ])
    assert _value(subj, "longitudinal_deviation_abs") == 2.0
    assert _value(subj, "bio_high_deviation_count") == 1.0


def test_source_diversity_and_corroboration():
    subj = multi_source_subject()
    assert _value(subj, "source_diversity") == 6.0  # NADO-TEST + CONFIDENTIAL + OSINT + LEO + ADAMS + BORDER
    # 3 reports claim DOPING from CONFIDENTIAL/OSINT/LEO
    assert _value(subj, "corroboration_count") == 3.0


def test_duplicate_reports_do_not_inflate_corroboration():
    subj = duplicate_reports_subject()
    assert _value(subj, "corroboration_count") == 1.0


def test_network_features():
    subj = network_subject()
    assert _value(subj, "relationship_degree") == 5.0
    assert _value(subj, "connected_entity_count") == 5.0
    assert _value(subj, "relationship_diversity") == 5.0
    assert _value(subj, "connected_alert_count") > 0


def test_report_reliability_weighted():
    subj = normal_subject()
    # single report weight 0.7 (C) -> weighted mean 0.7
    assert _value(subj, "report_reliability_weighted") == 0.7