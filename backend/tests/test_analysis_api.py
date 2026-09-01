"""Integration tests: full analysis run through the HTTP API with traceability."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.intelligence import IntelligenceReport, IntelligenceSource
from app.models.relationships import EntityRelationship, RelationshipType
from app.models.subjects import Athlete

ALICE = uuid.uuid4()
BOB = uuid.uuid4()
CAROL = uuid.uuid4()
DAN = uuid.uuid4()


TODAY = date.today()


def _ago(days: int) -> date:
    return TODAY - timedelta(days=days)


def _seed_source(db: Session, name: str, source_type: str, reliability: str = "C") -> IntelligenceSource:
    src = IntelligenceSource(name=name, source_type=source_type, reliability_default=reliability)
    db.add(src)
    db.flush()
    return src


def _seed_athlete(db: Session, sid: uuid.UUID, external_ref: str) -> Athlete:
    athlete = Athlete(
        id=sid,
        external_ref=external_ref,
        first_name="Test",
        last_name=external_ref,
        sport="CYCLING",
        status="ACTIVE",
    )
    db.add(athlete)
    db.flush()
    return athlete


def seed_domain(db: Session) -> None:
    lab = _seed_source(db, "National Lab", "NADO-TEST", "C")
    conf = _seed_source(db, "Confidential Source", "CONFIDENTIAL", "B")
    osint = _seed_source(db, "Open Source", "OSINT", "C")
    leo = _seed_source(db, "Law Enforcement", "LEO", "C")
    adams = _seed_source(db, "ADAMS", "ADAMS", "C")
    border = _seed_source(db, "Border Control", "BORDER", "C")

    rel_type = RelationshipType(name="TEAM_MEMBER", description="Same team/training group")
    db.add(rel_type)
    db.flush()

    _seed_athlete(db, ALICE, "ATH-ALICE")
    _seed_athlete(db, BOB, "ATH-BOB")
    carol = _seed_athlete(db, CAROL, "ATH-CAROL")
    dan = _seed_athlete(db, DAN, "ATH-DAN")

    def report(subject_id, days, src, category, reliability, title):
        db.add(
            IntelligenceReport(
                source_id=src.id,
                subject_type="ATHLETE",
                subject_id=subject_id,
                title=title,
                report_date=_ago(days),
                reliability=reliability,
                information_quality="2",
                info_category=category,
                status="NEW",
                is_duplicate=False,
            )
        )

    # --- ALICE: dense, multi-source, anomalous -------------------------------
    for days in (38, 30, 22):
        db.add(TestingEvent(athlete_id=ALICE, test_date=_ago(days), test_type="OUT_OF_COMPETITION", source_id=lab.id))
    db.add(BiologicalObservation(athlete_id=ALICE, observation_date=_ago(30), marker="HCT", value=3.1, baseline_deviation=3.1, source_id=lab.id))
    db.add(BiologicalObservation(athlete_id=ALICE, observation_date=_ago(29), marker="RET", value=2.9, baseline_deviation=2.9, source_id=lab.id))
    db.add(WhereaboutsEvent(athlete_id=ALICE, event_date=_ago(10), event_type="FILING", status="MISSED", source_id=adams.id))
    db.add(TravelEvent(athlete_id=ALICE, event_date=_ago(5), origin="LON", destination="LIM", event_type="INTERNATIONAL", source_id=border.id))
    db.add(MedicalEvent(athlete_id=ALICE, event_date=_ago(7), event_type="TUE_REVIEW", source_id=lab.id))
    db.add(SupplementEvent(athlete_id=ALICE, event_date=_ago(6), usage_note="imported product", source_id=lab.id))
    for days, src in ((20, conf), (18, osint), (16, leo), (12, lab)):
        report(ALICE, days, src, "DOPING", "B", "Suspected doping engagement")
    db.add(EntityRelationship(relationship_type_id=rel_type.id, from_entity_type="ATHLETE", from_entity_id=ALICE, to_entity_type="ATHLETE", to_entity_id=BOB, confidence=1.0, source_id=conf.id))
    db.add(EntityRelationship(relationship_type_id=rel_type.id, from_entity_type="ATHLETE", from_entity_id=ALICE, to_entity_type="ATHLETE", to_entity_id=CAROL, confidence=1.0, source_id=conf.id))
    db.add(EntityRelationship(relationship_type_id=rel_type.id, from_entity_type="ATHLETE", from_entity_id=ALICE, to_entity_type="ATHLETE", to_entity_id=DAN, confidence=1.0, source_id=conf.id))

    # --- BOB: moderate activity, single report, one relationship -------------
    for days in (90, 60, 30, 20, 10):
        db.add(TestingEvent(athlete_id=BOB, test_date=_ago(days), test_type="COMPETITION", source_id=lab.id))
    report(BOB, 25, conf, "GENERAL", "C", "General observation")
    db.add(EntityRelationship(relationship_type_id=rel_type.id, from_entity_type="ATHLETE", from_entity_id=BOB, to_entity_type="ATHLETE", to_entity_id=CAROL, confidence=0.8, source_id=conf.id))

    # --- CAROL / DAN: routine, low-volume ------------------------------------
    for days in (150, 120, 90):
        db.add(TestingEvent(athlete_id=CAROL, test_date=_ago(days), test_type="COMPETITION", source_id=lab.id))
    for days in (160, 130, 100):
        db.add(TestingEvent(athlete_id=DAN, test_date=_ago(days), test_type="COMPETITION", source_id=lab.id))
    db.flush()
    assert carol.id


def test_full_analysis_flow(analyst_client, db):
    seed_domain(db)
    db.commit()

    # --- start run -----------------------------------------------------------
    resp = analyst_client.post("/api/v1/analysis/runs", json={})
    assert resp.status_code == 201, resp.text
    run = resp.json()
    run_id = run["run_id"]

    # --- run retrieval -------------------------------------------------------
    detail = analyst_client.get(f"/api/v1/analysis/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "COMPLETED"
    assert body["result_count"] == 4
    assert body["result_counts"]["features"] == 4 * 17
    assert body["result_counts"]["priority"] == 4

    # --- per-stage endpoints -------------------------------------------------
    assert analyst_client.get(f"/api/v1/analysis/runs/{run_id}/features").json()["count"] == 68
    rules = analyst_client.get(f"/api/v1/analysis/runs/{run_id}/rules").json()
    assert rules["count"] > 0
    anomalies = analyst_client.get(f"/api/v1/analysis/runs/{run_id}/anomalies").json()
    assert anomalies["count"] == 4
    assert all(0 <= a["normalized_score"] <= 100 for a in anomalies["anomalies"])
    corrs = analyst_client.get(f"/api/v1/analysis/runs/{run_id}/correlations").json()
    assert corrs["count"] == 8  # temporal + cross_source per subject
    network = analyst_client.get(f"/api/v1/analysis/runs/{run_id}/network").json()
    assert network["count"] == 4
    priority = analyst_client.get(f"/api/v1/analysis/runs/{run_id}/priority").json()
    assert priority["count"] == 4

    # --- subject results -----------------------------------------------------
    subj = analyst_client.get(f"/api/v1/analysis/subjects/{ALICE}/results?run_id={run_id}")
    assert subj.status_code == 200
    subj_body = subj.json()
    assert len(subj_body["features"]) == 17
    assert subj_body["priority"]["subject_id"] == str(ALICE)

    # --- alerts: Alice elevated, Carol normal --------------------------------
    alerts = analyst_client.get("/api/v1/alerts", params={"run_id": run_id}).json()
    alert_subjects = [a["subject_id"] for a in alerts["alerts"]]
    assert str(ALICE) in alert_subjects
    assert str(CAROL) not in alert_subjects
    alice_alert = next(a for a in alerts["alerts"] if a["subject_id"] == str(ALICE))
    assert alice_alert["status"] == "NEW"
    assert alice_alert["priority_level"] in {"HIGH", "VERY_HIGH", "CRITICAL"}

    # --- priority ordering ---------------------------------------------------
    scored = analyst_client.get(f"/api/v1/analysis/runs/{run_id}/priority").json()["priority"]
    assert scored[0]["subject_id"] == str(ALICE)
    for row in scored:
        assert set(row) >= {
            "overall_score", "priority_level", "rule_score", "anomaly_score",
            "correlation_score", "temporal_score", "network_score", "source_quality_score",
        }

    # --- alert traceability --------------------------------------------------
    alert_detail = analyst_client.get(f"/api/v1/alerts/{alice_alert['id']}")
    assert alert_detail.status_code == 200
    ad = alert_detail.json()
    assert ad["priority"]["priority_level"] == alice_alert["priority_level"]
    signal_types = {s["signal_type"] for s in ad["signals"]}
    assert {"RULE", "ANOMALY", "TEMPORAL", "CROSS_SOURCE", "NETWORK"} <= signal_types
    assert len(ad["features"]) == 17
    for sig in ad["signals"]:
        assert "result" in sig

    # --- status review workflow ----------------------------------------------
    patch = analyst_client.patch(f"/api/v1/alerts/{alice_alert['id']}/status", json={"status": "REVIEWED"})
    assert patch.status_code == 200
    assert patch.json()["status"] == "REVIEWED"

    # --- run listing ---------------------------------------------------------
    listing = analyst_client.get("/api/v1/analysis/runs").json()
    assert listing["count"] >= 1


def test_unauthenticated_cannot_start_run(client):
    resp = client.post("/api/v1/analysis/runs", json={})
    assert resp.status_code == 401


def test_unauthenticated_can_read_runs(analyst_client, client):
    resp = analyst_client.post("/api/v1/analysis/runs", json={})
    assert resp.status_code == 201
    listing = client.get("/api/v1/analysis/runs").json()
    assert listing["count"] >= 1