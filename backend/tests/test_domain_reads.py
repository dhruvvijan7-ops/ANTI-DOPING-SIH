"""Domain read APIs (G3): dashboard, athletes/support persons, intelligence and
relationships. All assertions are against the real DB/API -- no fabricated data."""
from __future__ import annotations

import uuid

import pytest

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
from app.models.subjects import Athlete, SupportPerson

from tests.support_domain import ALICE, BOB, CAROL, DAN, seed_domain

ALL_ATHLETES = [ALICE, BOB, CAROL, DAN]


def _seed(db) -> None:
    seed_domain(db)
    db.commit()  # API clients use their own sessions; commit so reads see the rows


def _run_low_threshold_analysis(investigator_client) -> None:
    resp = investigator_client.post(
        "/api/v1/analysis/runs",
        json={
            "subject_ids": [str(a) for a in ALL_ATHLETES],
            "alert_threshold": "LOW",
        },
    )
    assert resp.status_code == 201, resp.text


# --- Dashboard --------------------------------------------------------------


def test_dashboard_reflects_real_analysis_activity(investigator_client, db):
    _seed(db)
    _run_low_threshold_analysis(investigator_client)

    resp = investigator_client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["alerts"]["total"] >= 1
    assert body["alerts"]["by_status"] != {}
    assert body["alerts"]["priority_distribution"] != {}
    assert body["alerts"]["recent"]
    assert body["investigations"]["total"] == 0
    assert body["intelligence"]["reports_total"] == 5
    assert body["entities"]["athletes_total"] == 4
    assert body["analysis"]["runs_total"] == 1


def test_dashboard_requires_authentication(client):
    assert client.get("/api/v1/dashboard").status_code == 401


def test_dashboard_without_data_returns_zero_counts(viewer_client, db):
    resp = viewer_client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["alerts"]["total"] == 0
    assert body["investigations"]["total"] == 0
    assert body["intelligence"]["reports_total"] == 0
    assert body["analysis"]["runs_total"] == 0
    assert body["entities"]["athletes_total"] == 0


# --- Athletes ---------------------------------------------------------------


def test_athletes_list_search_and_pagination(investigator_client, db):
    _seed(db)
    resp = investigator_client.get("/api/v1/athletes")
    assert resp.status_code == 200
    assert resp.json()["count"] == 4

    resp = investigator_client.get("/api/v1/athletes", params={"limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 4
    assert len(body["athletes"]) == 2

    resp = investigator_client.get("/api/v1/athletes", params={"q": "ALICE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["athletes"][0]["external_ref"] == "ATH-ALICE"


def test_athletes_require_authentication(client):
    assert client.get("/api/v1/athletes").status_code == 401


def test_athletes_list_rejects_page_limit_above_server_cap(investigator_client):
    resp = investigator_client.get("/api/v1/athletes", params={"limit": 250})
    assert resp.status_code == 422
    resp = investigator_client.get("/api/v1/athletes", params={"limit": 200})
    assert resp.status_code == 200


def test_viewer_can_read_athletes(viewer_client, db):
    _seed(db)
    assert viewer_client.get("/api/v1/athletes").status_code == 200


def test_athlete_detail_counts_and_profile(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Test ATH-ALICE"
    assert body["sport"] == "CYCLING"
    counts = body["counts"]
    assert counts["testing_events"] == 3
    assert counts["biological_observations"] == 2
    assert counts["whereabouts_events"] == 1
    assert counts["travel_events"] == 1
    assert counts["medical_events"] == 1
    assert counts["supplement_events"] == 1
    assert counts["intelligence_reports"] == 4
    assert counts["alerts"] == 0
    assert counts["relationships"] == 3


def test_athlete_404(investigator_client, db):
    assert investigator_client.get(f"/api/v1/athletes/{uuid.uuid4()}").status_code == 404


def test_athlete_testing_history(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}/tests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    dates = [t["test_date"] for t in body["tests"]]
    assert dates == sorted(dates, reverse=True)


def test_athlete_abp_filter(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}/abp")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2

    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}/abp", params={"marker": "HCT"})
    body = resp.json()
    assert body["count"] == 1
    assert body["observations"][0]["marker"] == "HCT"


def test_athlete_timeline_combines_events(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 13  # 3 tests + 2 ABP + 1 whereabouts + 1 travel + 1 medical + 1 supplement + 4 intel
    kinds = {e["kind"] for e in body["timeline"]}
    assert {"TESTING", "ABP", "WHEREABOUTS", "TRAVEL", "MEDICAL", "SUPPLEMENT", "INTELLIGENCE"} <= kinds
    dates = [e["date"] for e in body["timeline"]]
    assert dates == sorted(dates, reverse=True)


def test_athlete_intelligence_link(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}/intelligence")
    assert resp.status_code == 200
    assert resp.json()["count"] == 4


def test_athlete_relationships_resolved(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(f"/api/v1/athletes/{ALICE}/relationships")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    for rel in body["relationships"]:
        assert rel["from_name"] == "Test ATH-ALICE"
        assert rel["to_name"]
        assert rel["relationship_type"] == "TEAM_MEMBER"


# --- Support personnel -------------------------------------------------------


def test_support_person_reads(investigator_client, db):
    athlete = Athlete(
        id=uuid.uuid4(),
        external_ref="ATH-X",
        first_name="Case",
        last_name="Athlete",
        sport="WEIGHTLIFTING",
        status="ACTIVE",
    )
    db.add(athlete)
    coach = SupportPerson(name="Coach Vogel", support_role="COACH", country="DE", status="ACTIVE")
    db.add(coach)
    db.flush()
    rel_type = RelationshipType(name="COACH_ATHLETE", description="Coaching relationship")
    db.add(rel_type)
    db.flush()
    src = IntelligenceSource(name="Team Doctor", source_type="MEDICAL", confidentiality="INTERNAL")
    db.add(src)
    db.flush()
    db.add(
        EntityRelationship(
            relationship_type_id=rel_type.id,
            from_entity_type="SUPPORT_PERSON",
            from_entity_id=coach.id,
            to_entity_type="ATHLETE",
            to_entity_id=athlete.id,
            confidence=1.0,
            source_id=src.id,
        )
    )
    db.add(
        IntelligenceReport(
            source_id=src.id,
            subject_type="SUPPORT_PERSON",
            subject_id=coach.id,
            title="Coaching observation",
            info_category="GENERAL",
            status="NEW",
        )
    )
    db.commit()

    resp = investigator_client.get("/api/v1/support-persons")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = investigator_client.get(f"/api/v1/support-persons/{coach.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Coach Vogel"
    assert body["counts"]["relationships"] == 1
    assert body["counts"]["intelligence_reports"] == 1

    resp = investigator_client.get(f"/api/v1/support-persons/{coach.id}/relationships")
    assert resp.status_code == 200
    rel = resp.json()["relationships"][0]
    assert rel["from_name"] == "Coach Vogel"
    assert rel["to_name"] == "Case Athlete"

    resp = investigator_client.get(f"/api/v1/support-persons/{coach.id}/intelligence")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


# --- Intelligence ------------------------------------------------------------


def test_intelligence_list_filters_and_detail(investigator_client, db):
    _seed(db)
    resp = investigator_client.get("/api/v1/intelligence/reports", params={"subject_id": str(ALICE)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 4
    assert all(r["subject_name"] == "Test ATH-ALICE" for r in body["reports"])
    assert all(r["source"]["source_type"] for r in body["reports"])

    report_id = body["reports"][0]["id"]
    resp = investigator_client.get(f"/api/v1/intelligence/reports/{report_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == report_id
    assert detail["subject_name"] == "Test ATH-ALICE"
    assert detail["source"] is not None


def test_intelligence_requires_authentication(client):
    assert client.get("/api/v1/intelligence/reports").status_code == 401


def test_intelligence_list_rejects_page_limit_above_server_cap(investigator_client):
    resp = investigator_client.get("/api/v1/intelligence/reports", params={"limit": 250})
    assert resp.status_code == 422
    resp = investigator_client.get("/api/v1/intelligence/reports", params={"limit": 200})
    assert resp.status_code == 200


def test_intelligence_source_name_redacted_when_confidential(investigator_client, db):
    confidential = IntelligenceSource(
        name="Deep Human Asset",
        source_type="HUMINT",
        reliability_default="B",
        confidentiality="CONFIDENTIAL",
        is_active=True,
    )
    db.add(confidential)
    open_src = IntelligenceSource(
        name="Public Press",
        source_type="OSINT",
        reliability_default="C",
        confidentiality="INTERNAL",
        is_active=True,
    )
    db.add(open_src)
    db.flush()

    hidden = IntelligenceReport(source_id=confidential.id, title="Sensitive report", status="NEW")
    public = IntelligenceReport(source_id=open_src.id, title="Public report", status="NEW")
    db.add(hidden)
    db.add(public)
    db.commit()

    resp = investigator_client.get(f"/api/v1/intelligence/reports/{hidden.id}")
    assert resp.status_code == 200
    source = resp.json()["source"]
    assert source["name"] is None
    assert source["confidentiality"] == "CONFIDENTIAL"

    resp = investigator_client.get(f"/api/v1/intelligence/reports/{public.id}")
    assert resp.status_code == 200
    source = resp.json()["source"]
    assert source["name"] == "Public Press"
    assert source["confidentiality"] == "INTERNAL"


# --- Relationships ------------------------------------------------------------


def test_relationships_list_detail_and_filter(investigator_client, db):
    _seed(db)
    resp = investigator_client.get(
        "/api/v1/relationships",
        params={"entity_type": "ATHLETE", "entity_id": str(ALICE)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    first = body["relationships"][0]
    assert first["from_name"] == "Test ATH-ALICE"
    assert first["to_name"]
    assert first["relationship_type"] == "TEAM_MEMBER"

    resp = investigator_client.get("/api/v1/relationships", params={"relationship_type": "TEAM_MEMBER"})
    assert resp.json()["count"] == 3

    resp = investigator_client.get(f"/api/v1/relationships/{first['id']}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == first["id"]
    assert detail["from_entity_id"] == str(ALICE)


def test_relationships_require_authentication(client):
    assert client.get("/api/v1/relationships").status_code == 401


def test_relationships_404(investigator_client, db):
    assert investigator_client.get(f"/api/v1/relationships/{uuid.uuid4()}").status_code == 404