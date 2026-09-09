"""Phase D/E hardening integration tests.

Covers: investigation assignment (INVESTIGATIONS_ASSIGN enforcement + audit),
evidence sensitivity / integrity (sha256 over canonical content) / version
history / evidence-level authorization / controlled soft-delete, finding ->
evidence FK links with cross-investigation rejection, and the production
config fail-fast guard.

Every read re-opens a fresh session (PostgreSQL persistence, not in-memory).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.investigations.evidence_integrity import content_hash
from app.models.audit import AuditEvent
from app.models.identity import User
from app.models.investigations import EvidenceItem, EvidenceVersion, FindingEvidenceLink

from tests.support_domain import ALICE, seed_domain


def _create_case(client, title: str = "Hardening case") -> str:
    resp = client.post(
        "/api/v1/investigations",
        json={"title": title, "priority": "HIGH", "subject_type": "ATHLETE", "subject_id": str(ALICE)},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _add_evidence(client, inv_id: str, title: str = "Extract", sensitivity: str = "ROUTINE") -> str:
    resp = client.post(
        f"/api/v1/investigations/{inv_id}/evidence",
        json={"title": title, "evidence_type": "DOCUMENT", "source": "Lab",
              "classification": "CONFIDENTIAL", "sensitivity": sensitivity},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _add_finding(client, inv_id: str) -> str:
    resp = client.post(
        f"/api/v1/investigations/{inv_id}/findings",
        json={"title": "Preliminary assessment", "statement": "Signals justify continued review."},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _audit_events(db: Session, entity_type: str, entity_id: str) -> list[AuditEvent]:
    return db.query(AuditEvent).filter(
        AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id
    ).all()


# -------------------------------------------------------------------- assignment
def test_assignment_lifecycle_and_audit(db, investigator_client, viewer_client, analyst_client):
    seed_domain(db)
    db.commit()
    admin_id = db.scalar(select(User.id).where(User.username == "admin"))

    inv_id = _create_case(investigator_client)

    # investigator holds INVESTIGATIONS_ASSIGN -> 200 with prior/new metadata
    resp = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/assign",
        json={"assigned_to": str(admin_id), "note": "handing over"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["assigned_to"] == str(admin_id)
    assert resp.json()["assigned_to_name"] == "System Administrator"

    assigned = _audit_events(db, "INVESTIGATION", inv_id)
    actions = [e.action for e in assigned]
    assert "INVESTIGATION_ASSIGNED" in actions
    meta = [e for e in assigned if e.action == "INVESTIGATION_ASSIGNED"][0].metadata_json
    assert meta is not None

    # reassign to another real user records previous assignee
    viewer_id = db.scalar(select(User.id).where(User.username == "viewer"))
    resp = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": str(viewer_id)}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["assigned_to"] == str(viewer_id)

    # assigning the same user again is a no-op -> rejected
    same = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": str(viewer_id)}
    )
    assert same.status_code == 422

    # unassign: assigned_to = None
    resp = investigator_client.post(f"/api/v1/investigations/{inv_id}/assign", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["assigned_to"] is None

    # missing assignee / missing case -> 404
    nobody = uuid.uuid4()
    assert investigator_client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": str(nobody)}
    ).status_code == 404
    assert investigator_client.post(
        f"/api/v1/investigations/{uuid.uuid4()}/assign", json={"assigned_to": str(admin_id)}
    ).status_code == 404

    # creation with a nonexistent assignee is rejected
    bad_create = investigator_client.post(
        "/api/v1/investigations",
        json={"title": "Bad", "subject_type": "ATHLETE", "subject_id": str(ALICE),
              "assigned_to": str(nobody)},
    )
    assert bad_create.status_code == 404

    # list filter by assignee
    re = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": str(admin_id)}
    )
    assert re.status_code == 200
    listed = investigator_client.get(f"/api/v1/investigations?assigned_to={admin_id}").json()
    assert inv_id in {i["id"] for i in listed["investigations"]}


def test_assignment_permission_enforced(db, client, investigator_client, viewer_client, analyst_client):
    seed_domain(db)
    db.commit()
    inv_id = _create_case(investigator_client)
    admin_id = str(db.scalar(select(User.id).where(User.username == "admin")))

    # viewer and analyst do NOT hold INVESTIGATIONS_ASSIGN -> 403
    assert viewer_client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": admin_id}
    ).status_code == 403
    assert analyst_client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": admin_id}
    ).status_code == 403
    # unauthenticated -> 401
    assert client.post(
        f"/api/v1/investigations/{inv_id}/assign", json={"assigned_to": admin_id}
    ).status_code == 401


# ----------------------------------------------------------------------- evidence
def test_evidence_sensitivity_and_authorization(db, investigator_client, viewer_client, analyst_client):
    seed_domain(db)
    db.commit()
    inv_id = _create_case(investigator_client)
    routine_id = _add_evidence(investigator_client, inv_id, title="Routine", sensitivity="ROUTINE")
    sensitive_id = _add_evidence(investigator_client, inv_id, title="Sensitive", sensitivity="SENSITIVE")
    restricted_id = _add_evidence(investigator_client, inv_id, title="Restricted", sensitivity="RESTRICTED")

    # invalid sensitivity rejected
    bad = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/evidence",
        json={"title": "x", "evidence_type": "DOCUMENT", "sensitivity": "TOP_SECRET"},
    )
    assert bad.status_code == 422

    # viewer/analyst (no INVESTIGATIONS_MODIFY) only see ROUTINE/SENSITIVE
    viewer_seen = {e["id"] for e in viewer_client.get(f"/api/v1/investigations/{inv_id}/evidence").json()["evidence"]}
    assert viewer_seen == {routine_id, sensitive_id}
    analyst_seen = {e["id"] for e in analyst_client.get(f"/api/v1/investigations/{inv_id}/evidence").json()["evidence"]}
    assert analyst_seen == {routine_id, sensitive_id}

    # investigator sees everything
    investigator_seen = {e["id"] for e in investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence").json()["evidence"]}
    assert investigator_seen == {routine_id, sensitive_id, restricted_id}

    # detail-level authorization
    assert viewer_client.get(f"/api/v1/investigations/{inv_id}/evidence/{restricted_id}").status_code == 403
    assert analyst_client.get(f"/api/v1/investigations/{inv_id}/evidence/{restricted_id}").status_code == 403
    detail = investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{restricted_id}")
    assert detail.status_code == 200
    assert detail.json()["evidence"]["sensitivity"] == "RESTRICTED"


def test_evidence_integrity_and_version_history(db, investigator_client):
    seed_domain(db)
    db.commit()
    inv_id = _create_case(investigator_client)
    ev_id = _add_evidence(investigator_client, inv_id, title="Original extract")
    created = investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}").json()["evidence"]
    assert created["version"] == 1
    assert created["integrity"]["verified"] is True
    assert len(created["integrity"]["value"]) == 64

    versions = investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}/versions").json()
    assert versions["current_version"] == 1
    assert versions["count"] == 1
    assert versions["versions"][0]["change_reason"] == "Evidence item created"
    assert versions["versions"][0]["version"] == 1

    # patch -> new version, recomputed hash, persisted history
    first_hash = created["integrity"]["value"]
    patched = investigator_client.patch(
        f"/api/v1/investigations/{inv_id}/evidence/{ev_id}",
        json={"title": "Corrected extract", "change_reason": "adjusted title"},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["version"] == 2
    assert body["integrity"]["verified"] is True
    assert body["integrity"]["value"] != first_hash

    versions = investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}/versions").json()
    assert versions["count"] == 2
    assert [v["version"] for v in versions["versions"]] == [1, 2]
    assert versions["versions"][1]["title"] == "Corrected extract"
    assert versions["versions"][1]["change_reason"] == "adjusted title"

    # tampering out-of-band breaks verification
    item = db.scalar(select(EvidenceItem).where(EvidenceItem.id == uuid.UUID(ev_id)))
    item.title = "tampered in place"
    db.commit()
    tampered = investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}").json()["evidence"]
    assert tampered["integrity"]["verified"] is False

    # canonical hash is independently reproducible for the pre-tamper state
    original = db.scalar(select(EvidenceVersion).where(
        EvidenceVersion.evidence_id == uuid.UUID(ev_id),
        EvidenceVersion.version_number == 2,
    ))
    expected = content_hash({
        "title": "Corrected extract",
        "description": None,
        "evidence_type": "DOCUMENT",
        "source": "Lab",
        "classification": "CONFIDENTIAL",
        "sensitivity": "ROUTINE",
        "item_date": original.item_date,
        "relationship_to_case": None,
    })
    assert original.sha256_hash == expected


def test_evidence_soft_delete_preserves_links_and_history(db, investigator_client):
    seed_domain(db)
    db.commit()
    inv_id = _create_case(investigator_client)
    ev_id = _add_evidence(investigator_client, inv_id, title="Doomed extract")
    finding_id = _add_finding(investigator_client, inv_id)
    linked = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": ev_id, "validity": "SUPPORTING"},
    )
    assert linked.status_code == 200, linked.text

    deleted = investigator_client.delete(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] is True

    # list excludes, detail 404, deletion audited
    listed = {e["id"] for e in investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence").json()["evidence"]}
    assert ev_id not in listed
    assert investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}").status_code == 404
    assert any(e.action == "EVIDENCE_DELETED" for e in _audit_events(db, "EVIDENCE", ev_id))

    # overview count drops
    overview = investigator_client.get(f"/api/v1/investigations/{inv_id}").json()
    assert overview["counts"]["evidence"] == 0

    # version history preserved through the deletion, link still intact
    versions = investigator_client.get(f"/api/v1/investigations/{inv_id}/evidence/{ev_id}/versions")
    assert versions.status_code == 404  # deleted items are not directly readable
    finding = investigator_client.get(f"/api/v1/investigations/{inv_id}/findings").json()
    linked_finding = next(f for f in finding["findings"] if f["id"] == finding_id)
    assert [l["evidence_id"] for l in linked_finding["evidence_links"]] == [ev_id]


# ------------------------------------------------------------- finding-evidence links
def test_finding_evidence_links(db, investigator_client):
    seed_domain(db)
    db.commit()
    inv_id = _create_case(investigator_client)
    other_inv = _create_case(investigator_client, title="Separate case")
    ev_a = _add_evidence(investigator_client, inv_id, title="A")
    ev_b = _add_evidence(investigator_client, inv_id, title="B")
    cross_ev = _add_evidence(investigator_client, other_inv, title="Cross")
    finding_id = _add_finding(investigator_client, inv_id)

    # cross-investigation evidence rejected with 422
    cross = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": cross_ev, "validity": "SUPPORTING"},
    )
    assert cross.status_code == 422

    # missing evidence -> 404
    missing_ok = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": str(uuid.uuid4()), "validity": "SUPPORTING"},
    )
    assert missing_ok.status_code == 404

    # invalid validity -> 422
    bad_validity = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": ev_a, "validity": "MAYBE"},
    )
    assert bad_validity.status_code == 422

    # happy path + duplicate rejection
    ok = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": ev_a, "validity": "CONTRADICTING"},
    )
    assert ok.status_code == 200, ok.text
    assert [l["evidence_id"] for l in ok.json()["evidence_links"]] == [ev_a]
    assert ok.json()["evidence_links"][0]["validity"] == "CONTRADICTING"
    dup = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": ev_a, "validity": "SUPPORTING"},
    )
    assert dup.status_code == 409

    # second link to a different item
    ok2 = investigator_client.post(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence",
        json={"evidence_id": ev_b, "validity": "SUPPORTING"},
    )
    assert ok2.status_code == 200

    # unlink + 404 after removal
    unlink = investigator_client.delete(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence/{ev_a}"
    )
    assert unlink.status_code == 200, unlink.text
    assert [l["evidence_id"] for l in unlink.json()["evidence_links"]] == [ev_b]
    gone = investigator_client.delete(
        f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence/{ev_a}"
    )
    assert gone.status_code == 404

    # link row persisted (fresh session)
    links = db.query(FindingEvidenceLink).all()
    assert [(str(l.evidence_id), l.validity) for l in links] == [(ev_b, "SUPPORTING")]


def test_finding_evidence_link_permissions(db, investigator_client, analyst_client, viewer_client):
    seed_domain(db)
    db.commit()
    inv_id = _create_case(investigator_client)
    ev_id = _add_evidence(investigator_client, inv_id, title="E")
    finding_id = _add_finding(investigator_client, inv_id)
    payload = {"evidence_id": ev_id, "validity": "SUPPORTING"}
    assert analyst_client.post(f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence", json=payload).status_code == 403
    assert viewer_client.post(f"/api/v1/investigations/{inv_id}/findings/{finding_id}/evidence", json=payload).status_code == 403


# ----------------------------------------------------------------------- security guard
def test_production_config_guard(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    # dev default JWT secret with production env -> refuse to boot
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-dev-only")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "Str0ng-Prod-Passw0rd-2026!")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings().validate_production()

    # short secret -> refuse
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings().validate_production()

    # good secret but default admin password -> refuse
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "ChangeMeAdmin123!")
    with pytest.raises(RuntimeError, match="INITIAL_ADMIN_PASSWORD"):
        Settings().validate_production()

    # production-safe values -> pass
    monkeypatch.setenv("JWT_SECRET_KEY", "y" * 64)
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "UniqueStr0ng-Prod-Passw0rd-2042!")
    Settings().validate_production()

    # dev env accepts dev defaults
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-dev-only")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "ChangeMeAdmin123!")
    Settings().validate_production()