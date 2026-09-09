"""Runtime tests for the synthetic scenario system (G2 + G3 pipeline).

Covers catalog stability, deterministic generation, persistence/reset behaviour,
and per-scenario signal expectations through the full engine pipeline, using only
qualitative assertions (never hard-coded scores).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from app.analysis.contracts import AnalysisConfig, PRIORITY_LEVELS
from app.analysis.runner import run_analysis
from app.data.generators import build_scenario
from app.data.populate import populate, reset_synthetic
from app.data.registry import (
    BY_REF,
    SCENARIO_CORRELATED_ANOMALY,
    SCENARIO_FALSE_POSITIVE,
    SCENARIO_ISOLATED_ANOMALY,
    SCENARIO_MULTI_SOURCE,
    SCENARIO_NETWORK,
    SCENARIO_NORMAL,
    SCENARIO_TEMPORAL,
    SCENARIO_TYPES,
    catalog_summary,
)
from app.models.analytics import (
    Alert,
    CorrelationResult,
    NetworkResult,
    PriorityScore,
    RuleResult,
)
from app.models.relationships import EntityRelationship, RelationshipType
from app.models.scenarios import SyntheticScenario
from app.models.subjects import Athlete

AS_OF = date.today()


def _populate_and_run(db, ref: str, seed: int | None = None):
    populate(db, ref, seed=seed, as_of=AS_OF, reset_first=True)
    return run_analysis(db, config=AnalysisConfig())


def _priority(db, run_id, subject_id) -> PriorityScore:
    return db.scalar(
        select(PriorityScore).where(
            PriorityScore.analysis_run_id == run_id,
            PriorityScore.subject_id == subject_id,
        )
    )


def _rule(db, run_id, subject_id, rule_id) -> RuleResult | None:
    return db.scalar(
        select(RuleResult).where(
            RuleResult.analysis_run_id == run_id,
            RuleResult.subject_id == subject_id,
            RuleResult.rule_id == rule_id,
        )
    )


def _corr(db, run_id, subject_id, kind) -> CorrelationResult | None:
    return db.scalar(
        select(CorrelationResult).where(
            CorrelationResult.analysis_run_id == run_id,
            CorrelationResult.subject_id == subject_id,
            CorrelationResult.correlation_type == kind,
        )
    )


def _target(db) -> Athlete:
    return db.scalar(select(Athlete).order_by(Athlete.external_ref.asc()))


# --------------------------------------------------------------------------- registry


def test_catalog_is_complete_and_stable():
    rows = catalog_summary()
    assert len(rows) == 7
    refs = [r["ref"] for r in rows]
    assert len(refs) == len(set(refs)) == 7
    assert refs[0] == SCENARIO_NORMAL
    for r in rows:
        assert r["scenario_type"] in SCENARIO_TYPES
        assert "_".join(r["ref"].split("_")[1:-1]) == r["scenario_type"]
    seeds = [r["seed"] for r in rows]
    assert len(seeds) == len(set(seeds))
    assert BY_REF[SCENARIO_FALSE_POSITIVE].ground_truth


def test_registry_ground_truth_is_evaluation_only():
    # labels must never assert real-world established guilt
    for spec in BY_REF.values():
        assert "guilt" not in spec.ground_truth.lower()
        assert "no real" not in spec.ground_truth.lower()


# --------------------------------------------------------------------------- determinism


def test_generation_is_deterministic():
    a = build_scenario(BY_REF[SCENARIO_NORMAL], seed=1234, as_of=AS_OF)
    b = build_scenario(BY_REF[SCENARIO_NORMAL], seed=1234, as_of=AS_OF)
    assert [at.id for at in a.athletes] == [at.id for at in b.athletes]
    assert [r.id for r in a.reports] == [r.id for r in b.reports]
    assert a.summary() == b.summary()
    c = build_scenario(BY_REF[SCENARIO_NORMAL], seed=9999, as_of=AS_OF)
    assert a.athletes[0].id != c.athletes[0].id
    assert a.athletes[1].id != c.athletes[1].id


def test_default_seeds_are_stable_ids():
    a = build_scenario(BY_REF[SCENARIO_ISOLATED_ANOMALY], seed=1201, as_of=AS_OF)
    b = build_scenario(BY_REF[SCENARIO_ISOLATED_ANOMALY], seed=1201, as_of=AS_OF)
    assert a.target is not None and a.target.id == b.target.id


def test_scenario_target_is_first_athlete():
    for ref in (SCENARIO_ISOLATED_ANOMALY, SCENARIO_CORRELATED_ANOMALY):
        seth = build_scenario(BY_REF[ref], as_of=AS_OF)
        assert seth.target is not None
        assert seth.target.external_ref == "SYN-ATH-000"


# --------------------------------------------------------------------------- persistence / reset


def test_populate_persists_scenario_and_target(db):
    populate(db, SCENARIO_ISOLATED_ANOMALY, seed=1201, as_of=AS_OF, reset_first=True)
    assert db.scalar(select(func.count(Athlete.id))) == 14
    row = db.scalar(select(SyntheticScenario).where(SyntheticScenario.scenario_ref == SCENARIO_ISOLATED_ANOMALY))
    assert row is not None
    target = db.scalar(select(Athlete).order_by(Athlete.external_ref.asc()))
    assert row.subject_type == "ATHLETE"
    assert row.subject_id == target.id
    assert "seed" in (row.extra_refs or "")


def test_reset_clears_synthetic_domain(db):
    populate(db, SCENARIO_MULTI_SOURCE, as_of=AS_OF, reset_first=True)
    assert db.scalar(select(func.count(Athlete.id))) == 14
    reset_synthetic(db)
    assert db.scalar(select(func.count(Athlete.id))) == 0
    assert db.scalar(select(func.count(SyntheticScenario.id))) == 0
    assert db.scalar(select(func.count(RelationshipType.id))) == 0
    assert db.scalar(select(func.count(EntityRelationship.id))) == 0


def test_persist_rejects_unknown_scenario(db):
    try:
        populate(db, "SCENARIO_NOPE_999", as_of=AS_OF, reset_first=True)
        raised = False
    except ValueError:
        raised = True
    assert raised


# --------------------------------------------------------------------------- pipeline signals


def test_normal_scenario_has_no_concentrated_signal(db):
    run = _populate_and_run(db, SCENARIO_NORMAL)
    assert run.status == "COMPLETED"
    target = _target(db)
    prio = _priority(db, run.id, target.id)
    assert prio is not None
    assert prio.priority_level in PRIORITY_LEVELS
    assert prio.priority_level != "CRITICAL"
    assert _rule(db, run.id, target.id, "RULES-005") is None or not _rule(db, run.id, target.id, "RULES-005").triggered
    assert _rule(db, run.id, target.id, "RULES-008") is None or not _rule(db, run.id, target.id, "RULES-008").triggered


def test_isolated_anomaly_triggers_biological_rule(db):
    run = _populate_and_run(db, SCENARIO_ISOLATED_ANOMALY)
    target = _target(db)
    rule = _rule(db, run.id, target.id, "RULES-005")
    assert rule is not None and rule.triggered
    corr = _corr(db, run.id, target.id, "CROSS_SOURCE")
    assert corr is not None and corr.score <= 50.0


def test_temporal_scenario_produces_cluster_signals(db):
    run = _populate_and_run(db, SCENARIO_TEMPORAL)
    target = _target(db)
    temporal = _corr(db, run.id, target.id, "TEMPORAL")
    assert temporal is not None
    assert temporal.score > 0.0
    assert temporal.signal_count >= 3
    fail = _rule(db, run.id, target.id, "RULES-008")
    assert fail is not None and fail.triggered
    assert _corr(db, run.id, target.id, "CROSS_SOURCE").score == 0.0


def test_multi_source_produces_corroboration(db):
    run = _populate_and_run(db, SCENARIO_MULTI_SOURCE)
    target = _target(db)
    corr = _corr(db, run.id, target.id, "CROSS_SOURCE")
    assert corr is not None and corr.score > 0.0
    assert corr.category_count >= 2
    assert _rule(db, run.id, target.id, "RULES-002").triggered
    assert _rule(db, run.id, target.id, "RULES-001").triggered


def test_network_scenario_elevates_target(db):
    run = _populate_and_run(db, SCENARIO_NETWORK)
    target = _target(db)
    net = db.scalar(
        select(NetworkResult).where(
            NetworkResult.analysis_run_id == run.id,
            NetworkResult.subject_id == target.id,
        )
    )
    assert net is not None
    assert net.degree >= 8
    assert net.score > 0.0


def test_correlated_anomaly_shows_multiple_signal_categories(db):
    run = _populate_and_run(db, SCENARIO_CORRELATED_ANOMALY)
    target = _target(db)
    cat = 0
    if _rule(db, run.id, target.id, "RULES-005").triggered:
        cat += 1
    if (_corr(db, run.id, target.id, "TEMPORAL") or None) is not None and _corr(db, run.id, target.id, "TEMPORAL").signal_count:
        cat += 1
    if _corr(db, run.id, target.id, "CROSS_SOURCE").signal_count:
        cat += 1
    net = db.scalar(
        select(NetworkResult).where(
            NetworkResult.analysis_run_id == run.id,
            NetworkResult.subject_id == target.id,
        )
    )
    if net.degree >= 3:
        cat += 1
    assert cat >= 3


def test_correlated_anomaly_generates_alerts(db):
    run = _populate_and_run(db, SCENARIO_CORRELATED_ANOMALY)
    alerts = db.scalars(select(Alert).where(Alert.analysis_run_id == run.id)).all()
    assert len(alerts) >= 1


def test_false_positive_stays_reviewable(db):
    run = _populate_and_run(db, SCENARIO_FALSE_POSITIVE)
    target = _target(db)
    prio = _priority(db, run.id, target.id)
    assert prio is not None
    assert prio.overall_score < 70.0
    assert prio.priority_level != "CRITICAL"
    assert prio.priority_level in {"LOW", "MODERATE", "HIGH", "VERY_HIGH"}
    # the signal must still be visible for review (rule fires), just not terminal
    assert _rule(db, run.id, target.id, "RULES-005").triggered


def test_quality_ordering_isolated_vs_correlated(db):
    run_iso = _populate_and_run(db, SCENARIO_ISOLATED_ANOMALY)
    iso_id = _target(db).id
    run_corr = _populate_and_run(db, SCENARIO_CORRELATED_ANOMALY)
    corr_id = _target(db).id
    iso = _priority(db, run_iso.id, iso_id)
    corr = _priority(db, run_corr.id, corr_id)
    assert iso is not None and corr is not None
    assert corr.overall_score > iso.overall_score