"""Unit tests for the deterministic rule registry + engine."""
from __future__ import annotations

from app.analysis.contracts import AnalysisConfig, SubjectData
from app.analysis.features import compute_features
from app.analysis.rules import evaluate_rules, rule_catalog
from tests.support_analytics import (
    AS_OF,
    make_signal,
    make_subject,
    multi_source_subject,
    network_subject,
    normal_subject,
)

CFG = AnalysisConfig()


def _fire(subject: SubjectData):
    features = compute_features(subject, CFG, AS_OF)
    outcomes, score = evaluate_rules(subject, features, CFG, AS_OF)
    return [o for o in outcomes if o.triggered], score, outcomes


def test_no_trigger_for_normal_subject():
    fired, score, _ = _fire(normal_subject())
    assert fired == []
    assert score == 0.0


def test_missing_data_never_triggers():
    fired, score, _ = _fire(make_subject())
    assert fired == []
    assert score == 0.0


def test_corroboration_and_multi_category_trigger():
    fired, score, _ = _fire(multi_source_subject())
    ids = {o.rule_id for o in fired}
    assert "RULES-002" in ids  # independent corroboration
    assert "RULES-007" in ids  # >=4 distinct categories


def test_high_reliability_rule():
    subj = make_subject([
        make_signal(category="REPORT", days_ago=5, source_category="CONFIDENTIAL", info_category="X", weight=0.9, reliability="A"),
    ])
    fired, _, _ = _fire(subj)
    ids = {o.rule_id for o in fired}
    assert "RULES-004" in ids


def test_whereabouts_failure_rule():
    subj = make_subject([
        make_signal(category="WHEREABOUTS", days_ago=3, status="MISSED", weight=1.0),
    ])
    fired, _, _ = _fire(subj)
    assert {"RULES-008"} <= {o.rule_id for o in fired}


def test_triggers_are_structured_and_explained():
    fired, _, _ = _fire(multi_source_subject())
    assert fired
    for o in fired:
        assert o.rule_id and o.name and o.severity and o.expression
        assert isinstance(o.conditions_met, list)
        assert o.detail


def test_catalog_carries_enable_flag_and_config():
    for row in rule_catalog():
        assert row["rule_id"]
        assert "is_enabled" in row
        assert row["conditions_json"]


def test_network_density_rule():
    fired, _, _ = _fire(network_subject())
    assert "RULES-006" in {o.rule_id for o in fired}