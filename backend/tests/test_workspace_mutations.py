"""Workspace gate integration tests: manual timeline entries, manual
intelligence recording and manual relationship recording.

Each of these is human-authored work product (never engine-generated):
  - timeline: analyst-placed reconstruction events (INVESTIGATIONS_MODIFY)
  - intelligence: analyst-recorded reports from an existing source
    (INTELLIGENCE_CREATE); they must appear in the case intelligence tab
  - relationships: descriptive associations, recorded by analysts/investigators
    (INTELLIGENCE_CREATE or INVESTIGATIONS_MODIFY)
Viewer is read-only everywhere.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

from tests.support_domain import ALICE, BOB, seed_domain


def _create_case(investigator_client) -> str:
    resp = investigator_client.post(
        "/api/v1/investigations",
        json={
            "title": "Workspace gate case",
            "priority": "HIGH",
            "subject_type": "ATHLETE",
            "subject_id": str(ALICE),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _audit_actions(db: Session, entity_type: str, entity_id: str) -> list[str]:
    rows = db.query(AuditEvent).filter(
        AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id
    ).all()
    return [r.action for r in rows]


def test_manual_timeline_entry_persists_and_is_audited(
    admin_client, investigator_client, viewer_client, db: Session
):
    seed_domain(db)
    db.commit()
    investigation_id = _create_case(investigator_client)

    # viewer cannot place entries
    blocked = viewer_client.post(
        f"/api/v1/investigations/{investigation_id}/timeline",
        json={"occurred_at": "2026-08-01T10:00:00", "summary": "nope", "event_type": "MANUAL"},
    )
    assert blocked.status_code == 403

    created = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/timeline",
        json={
            "occurred_at": "2026-08-01T10:00:00",
            "summary": "Source interview: corroborated training group membership",
            "event_type": "interview",
            "source": "CONF-HANDLER-01",
        },
    )
    assert created.status_code == 200, created.text
    entry = created.json()
    assert entry["origin"] == "timeline_events"
    assert entry["event_type"] == "INTERVIEW"

    # blank summary rejected
    blank = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/timeline",
        json={"occurred_at": "2026-08-01T10:00:00", "summary": "   "},
    )
    assert blank.status_code == 422

    timeline = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/timeline"
    ).json()
    assert any(
        t["origin"] == "timeline_events" and t["record_id"] == entry["id"]
        for t in timeline["timeline"]
    )

    audit = admin_client.get(
        f"/api/v1/investigations/{investigation_id}/audit"
    ).json()
    assert any(
        a["action"] == "TIMELINE_ENTRY_CREATED" and a["entity_id"] == entry["id"]
        for a in audit["audit"]
    )


def test_manual_intelligence_report_appears_in_case_and_lists(
    investigator_client, analyst_client, viewer_client, db: Session
):
    seed_domain(db)
    db.commit()
    investigation_id = _create_case(investigator_client)

    # viewer cannot record intelligence
    blocked = viewer_client.post(
        "/api/v1/intelligence/reports",
        json={
            "source_id": "00000000-0000-0000-0000-000000000000",
            "title": "nope",
        },
    )
    assert blocked.status_code == 403

    sources = analyst_client.get("/api/v1/intelligence/sources").json()
    src = next(s for s in sources["sources"] if s["source_type"] == "OSINT")

    created = analyst_client.post(
        "/api/v1/intelligence/reports",
        json={
            "source_id": src["source_id"],
            "title": "Manual report: training-group association",
            "description": "Recorded by the analyst from an open-source check.",
            "subject_type": "ATHLETE",
            "subject_id": str(ALICE),
            "report_date": "2026-08-05",
            "reliability": "C",
            "information_quality": "3",
            "confidentiality": "INTERNAL",
            "status": "NEW",
            "info_category": "SOURCE_OBSERVATION",
        },
    )
    assert created.status_code == 200, created.text
    report_id = created.json()["id"]
    assert created.json()["subject_id"] == str(ALICE)

    # appears in the case intelligence tab (4 seeded + manual)
    case_intel = analyst_client.get(
        f"/api/v1/investigations/{investigation_id}/intelligence"
    ).json()
    assert case_intel["count"] == 5
    assert any(r["id"] == report_id for r in case_intel["intelligence"])

    # appears in the global intelligence list
    listing = analyst_client.get("/api/v1/intelligence/reports", params={"q": "training-group"}).json()
    assert any(r["id"] == report_id for r in listing["reports"])

    # validation: unknown source / no subject pairing / unsupported type
    bad_source = analyst_client.post(
        "/api/v1/intelligence/reports",
        json={"source_id": str(uuid.uuid4()), "title": "x"},
    )
    assert bad_source.status_code == 404

    lone_subject = analyst_client.post(
        "/api/v1/intelligence/reports",
        json={"source_id": src["source_id"], "title": "x", "subject_type": "ATHLETE"},
    )
    assert lone_subject.status_code == 422

    bad_type = analyst_client.post(
        "/api/v1/intelligence/reports",
        json={
            "source_id": src["source_id"],
            "title": "x",
            "subject_type": "BANANA",
            "subject_id": str(ALICE),
        },
    )
    assert bad_type.status_code == 422

    # audit recorded on the create path (entity-scoped event, checked at DB level)
    assert "INTELLIGENCE_CREATED" in _audit_actions(db, "INTELLIGENCE_REPORT", report_id)


def test_manual_relationship_recording_and_validation(
    investigator_client, analyst_client, viewer_client, db: Session
):
    seed_domain(db)
    db.commit()
    investigation_id = _create_case(investigator_client)

    # type vocabulary is listable
    types = analyst_client.get("/api/v1/relationships/types").json()
    assert "TEAM_MEMBER" in {t["name"] for t in types["types"]}

    # viewer cannot record
    blocked = viewer_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TEAM_MEMBER",
        },
    )
    assert blocked.status_code == 403

    # analyst creates a NEW association with a NOT-yet-seeded type (auto-created)
    created = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "travel_companion",
            "confidence": 0.8,
            "start_date": "2026-01-01",
        },
    )
    assert created.status_code == 200, created.text
    rel_id = created.json()["id"]
    assert created.json()["relationship_type"] == "TRAVEL_COMPANION"

    # appears in the case relationship graph (subject ALICE)
    graph = analyst_client.get(
        f"/api/v1/investigations/{investigation_id}/relationships"
    ).json()
    assert any(
        e["data"]["relationship_type"] == "TRAVEL_COMPANION" and e["data"]["relationship_id"] == rel_id
        for e in graph["edges"]
    )

    # duplicate exact association -> 409
    dup = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TRAVEL_COMPANION",
        },
    )
    assert dup.status_code == 409

    # validation
    bad_entity = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(uuid.uuid4()),
            "relationship_type": "TEAM_MEMBER",
        },
    )
    assert bad_entity.status_code == 422
    assert "does not exist" in bad_entity.json()["error"]["message"]

    self_rel = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(ALICE),
            "relationship_type": "TEAM_MEMBER",
        },
    )
    assert self_rel.status_code == 422

    bad_conf = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TEAM_MEMBER",
            "confidence": 1.5,
        },
    )
    assert bad_conf.status_code == 422

    unknown_source = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "ATHLETE",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TEAM_MEMBER",
            "source_id": str(uuid.uuid4()),
        },
    )
    assert unknown_source.status_code == 422

    bad_kind = analyst_client.post(
        "/api/v1/relationships",
        json={
            "from_entity_type": "BANANA",
            "from_entity_id": str(ALICE),
            "to_entity_type": "ATHLETE",
            "to_entity_id": str(BOB),
            "relationship_type": "TEAM_MEMBER",
        },
    )
    assert bad_kind.status_code == 422

    # audit recorded (entity-scoped event, checked at DB level)
    assert "RELATIONSHIP_CREATED" in _audit_actions(db, "RELATIONSHIP", rel_id)