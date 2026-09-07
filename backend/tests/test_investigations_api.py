"""Integration tests: alert triage -> investigation workspace (STAGE F/G).

The full workflow (Alert -> Review -> Convert -> Investigation -> Evidence -> Task
-> Note -> Finding -> Audit) must survive across HTTP requests, because every read
re-opens a fresh DB session: PostgreSQL persistence, not in-memory state.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

from tests.support_domain import ALICE, BOB, CAROL, DAN, seed_domain


def _find_alert(client, run_id: uuid.UUID, subject_id: uuid.UUID):
    body = client.get("/api/v1/alerts", params={"run_id": str(run_id)}).json()
    for alert in body["alerts"]:
        if alert["subject_id"] == str(subject_id):
            return alert
    raise AssertionError(f"no alert for {subject_id} in run {run_id}: {body}")


def _run_analysis(client, subject_ids=None) -> uuid.UUID:
    payload = {"subject_ids": [str(s) for s in subject_ids]} if subject_ids else {}
    resp = client.post("/api/v1/analysis/runs", json=payload)
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["run_id"])


def _audit_actions(db: Session, entity_type: str, entity_id: str) -> list[str]:
    rows = db.query(AuditEvent).filter(
        AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id
    ).all()
    return [r.action for r in rows]


def test_triage_workflow_persists_across_requests(analyst_client, investigator_client, db):
    seed_domain(db)
    db.commit()

    run_id = _run_analysis(analyst_client)

    # --- alert created by the engine ----------------------------------------
    alerts = analyst_client.get("/api/v1/alerts", params={"run_id": str(run_id)}).json()
    subjects = {a["subject_id"] for a in alerts["alerts"]}
    assert str(ALICE) in subjects
    assert str(CAROL) not in subjects

    alert = _find_alert(analyst_client, run_id, ALICE)
    alert_id = alert["id"]

    # --- review --------------------------------------------------------------
    reviewed = analyst_client.post(f"/api/v1/alerts/{alert_id}/review", json={"note": "reviewing"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "REVIEWED"
    assert "ALERT_REVIEWED" in _audit_actions(db, "ALERT", alert_id)

    # --- escalate ------------------------------------------------------------
    escalated = analyst_client.post(f"/api/v1/alerts/{alert_id}/escalate", json={"note": "escalate"})
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "ESCALATED"
    assert "ALERT_ESCALATED" in _audit_actions(db, "ALERT", alert_id)

    # --- convert to investigation (investigator decision) ---------------------
    converted = investigator_client.post(f"/api/v1/alerts/{alert_id}/convert", json={"priority": "VERY_HIGH"})
    assert converted.status_code == 200, converted.text
    investigation_id = uuid.UUID(converted.json()["investigation"]["id"])
    assert converted.json()["investigation"]["status"] == "OPEN"
    assert converted.json()["investigation"]["priority"] == "VERY_HIGH"

    # conversion persisted on the alert side
    detail = analyst_client.get(f"/api/v1/alerts/{alert_id}").json()
    assert detail["alert"]["status"] == "CONVERTED"
    assert detail["alert"]["investigation_id"] == str(investigation_id)

    # --- case work, each action recorded as case records ---------------
    evidence = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"title": "Lab record extract", "evidence_type": "DOCUMENT",
              "classification": "CONFIDENTIAL", "source": "National Lab"},
    )
    assert evidence.status_code == 200, evidence.text
    evidence_id = evidence.json()["id"]

    task = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/tasks",
        json={"title": "Interview source", "status": "OPEN"},
    )
    assert task.status_code == 200, task.text
    task_id = task.json()["id"]

    note = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/notes",
        json={"content": "First case note by the investigator."},
    )
    assert note.status_code == 200, note.text
    note_id = note.json()["id"]

    finding = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={"title": "Preliminary assessment",
              "statement": "The analytical signals justify continued review.",
              "assessment": "ASSESSED", "confident": False},
    )
    assert finding.status_code == 200, finding.text
    finding_id = finding.json()["id"]

    # --- every GET below is a fresh session: proves persistence ----------
    overview = investigator_client.get(f"/api/v1/investigations/{investigation_id}").json()
    assert overview["investigation"]["case_ref"].startswith("CASE-")
    assert overview["originating_alert"]["alert_ref"].startswith("ALERT-")
    assert overview["counts"] == {"alerts": 1, "evidence": 1, "tasks": 1, "notes": 1, "findings": 1, "reports": 0}

    intelligence = investigator_client.get(f"/api/v1/investigations/{investigation_id}/intelligence").json()
    assert intelligence["count"] == 4  # ALICE has 4 reports

    timeline = investigator_client.get(f"/api/v1/investigations/{investigation_id}/timeline").json()
    assert timeline["count"] > 0
    assert any(t["event_type"] == "EVIDENCE" and t["record_id"] == evidence_id for t in timeline["timeline"])
    assert any(t["event_type"] == "NOTE" and t["record_id"] == note_id for t in timeline["timeline"])
    assert any(t["relevance"] == "ALERT_SIGNAL" for t in timeline["timeline"])

    ev_list = investigator_client.get(f"/api/v1/investigations/{investigation_id}/evidence").json()
    assert [e["id"] for e in ev_list["evidence"]] == [evidence_id]

    tasks = investigator_client.get(f"/api/v1/investigations/{investigation_id}/tasks").json()
    assert [t["id"] for t in tasks["tasks"]] == [task_id]

    notes = investigator_client.get(f"/api/v1/investigations/{investigation_id}/notes").json()
    assert [n["id"] for n in notes["notes"]] == [note_id]

    findings = investigator_client.get(f"/api/v1/investigations/{investigation_id}/findings").json()
    assert [f["id"] for f in findings["findings"]] == [finding_id]

    graph = investigator_client.get(f"/api/v1/investigations/{investigation_id}/relationships").json()
    assert graph["node_count"] == 4  # subject + BOB/CAROL/DAN
    assert graph["edge_count"] == 3
    assert "do not imply wrongdoing" in graph["note"]
    assert {n["id"] for n in graph["nodes"]} == {
        f"ATHLETE:{ALICE}", f"ATHLETE:{BOB}", f"ATHLETE:{CAROL}", f"ATHLETE:{DAN}"
    }

    # --- audit trail shows who did what on which object -------------------
    audit = investigator_client.get(f"/api/v1/investigations/{investigation_id}/audit").json()
    actions = {a["action"] for a in audit["audit"]}
    assert {"INVESTIGATION_CREATED", "ALERT_CONVERTED", "EVIDENCE_CREATED",
            "TASK_CREATED", "NOTE_CREATED", "FINDING_CREATED"} <= actions
    assert all(a["actor"] is not None for a in audit["audit"])

    # --- task update -------------------------------------------------------
    updated = investigator_client.patch(
        f"/api/v1/investigations/{investigation_id}/tasks/{task_id}",
        json={"status": "DONE"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "DONE"

    # --- close -------------------------------------------------------------
    closed = investigator_client.post(f"/api/v1/investigations/{investigation_id}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"
    assert "INVESTIGATION_CLOSED" in _audit_actions(db, "INVESTIGATION", str(investigation_id))


def test_dismiss_and_false_positive_actions(investigator_client, db):
    seed_domain(db)
    db.commit()

    # dismissal is an investigator decision: ALERTS_DISMISS is granted to
    # INVESTIGATOR/ADMIN only, not to the analytics role.
    run_b = _run_analysis(investigator_client, subject_ids=[ALICE])
    alert_b = _find_alert(investigator_client, run_b, ALICE)
    dismissed = investigator_client.post(f"/api/v1/alerts/{alert_b['id']}/dismiss")
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "DISMISSED"
    assert "ALERT_DISMISSED" in _audit_actions(db, "ALERT", alert_b["id"])

    run_c = _run_analysis(investigator_client, subject_ids=[ALICE])
    alert_c = _find_alert(investigator_client, run_c, ALICE)
    fp = investigator_client.post(f"/api/v1/alerts/{alert_c['id']}/false-positive", json={"note": "biofluctuation"})
    assert fp.status_code == 200
    assert fp.json()["status"] == "FALSE_POSITIVE"
    assert "ALERT_MARKED_FALSE_POSITIVE" in _audit_actions(db, "ALERT", alert_c["id"])


def test_unauthorized_users_blocked(client, viewer_client, analyst_client, investigator_client, db):
    seed_domain(db)
    db.commit()

    listing = client.get("/api/v1/investigations")  # unauthenticated
    assert listing.status_code == 401

    viewer_listing = viewer_client.get("/api/v1/investigations")
    assert viewer_listing.status_code == 200  # viewer is authorized to read cases

    run_id = _run_analysis(analyst_client, subject_ids=[ALICE])
    alert = _find_alert(analyst_client, run_id, ALICE)

    # viewer cannot review alerts
    blocked_review = viewer_client.post(f"/api/v1/alerts/{alert['id']}/review")
    assert blocked_review.status_code == 403

    converted = investigator_client.post(f"/api/v1/alerts/{alert['id']}/convert")
    assert converted.status_code == 200
    investigation_id = converted.json()["investigation"]["id"]

    # viewer can read (authorized) but cannot create evidence/notes/findings
    ok_read = viewer_client.get(f"/api/v1/investigations/{investigation_id}")
    assert ok_read.status_code == 200

    blocked_evidence = viewer_client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"title": "x", "evidence_type": "DOCUMENT"},
    )
    assert blocked_evidence.status_code == 403

    blocked_note = viewer_client.post(
        f"/api/v1/investigations/{investigation_id}/notes",
        json={"content": "x"},
    )
    assert blocked_note.status_code == 403

    # analyst (INTELLIGENCE_ANALYST) has EVIDENCE_CREATE but not INVESTIGATIONS_MODIFY
    # -> can add evidence but cannot create findings.
    ok_evidence = analyst_client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"title": "open-source screenshot", "evidence_type": "SCREENSHOT"},
    )
    assert ok_evidence.status_code == 200
    blocked_finding = analyst_client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={"title": "t", "statement": "s"},
    )
    assert blocked_finding.status_code == 403


def test_direct_investigation_creation(analyst_client, db):
    seed_domain(db)
    db.commit()
    resp = analyst_client.post(
        "/api/v1/investigations",
        json={
            "title": "Direct case",
            "priority": "HIGH",
            "subject_type": "ATHLETE",
            "subject_id": str(ALICE),
        },
    )
    assert resp.status_code == 200, resp.text
    inv = resp.json()
    assert inv["status"] == "OPEN"
    assert inv["originating_alert_id"] is None
    assert inv["case_ref"].startswith("CASE-")