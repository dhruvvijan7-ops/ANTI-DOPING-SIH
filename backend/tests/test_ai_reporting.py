"""Integration tests: AI decision support + versioned reporting (STAGE H/I).

Covers: retrieval is scoped to the case (no unrelated data sent), the fallback
provider is used when no LLM is configured, output never invents records, reports
are grounded in real case data, and restricted operations are permission-guarded.
"""
from __future__ import annotations

import uuid

from tests.support_domain import ALICE, CAROL, seed_domain

PROHIBITED = ("guilty", "sanction", "confirmed doping", "prohibited substance detected")


def _find_alert(client, run_id: uuid.UUID, subject_id: uuid.UUID):
    body = client.get("/api/v1/alerts", params={"run_id": str(run_id)}).json()
    for alert in body["alerts"]:
        if alert["subject_id"] == str(subject_id):
            return alert
    raise AssertionError(f"no alert for {subject_id}: {body}")


def _convert_alice(analyst_client) -> str:
    resp = analyst_client.post("/api/v1/analysis/runs", json={})
    assert resp.status_code == 201, resp.text
    run_id = uuid.UUID(resp.json()["run_id"])
    alert = _find_alert(analyst_client, run_id, ALICE)
    converted = analyst_client.post(f"/api/v1/alerts/{alert['id']}/convert")
    assert converted.status_code == 200, converted.text
    return converted.json()["investigation"]["id"]


def _all_statements(blocks: list[dict]) -> list[str]:
    texts = []
    for block in blocks:
        if isinstance(block, dict) and "content" in block:
            texts.extend(item["statement"] for item in block["content"])
        elif isinstance(block, dict) and "draft" in block:
            texts.append(str(block["draft"]))
    return texts


def test_ai_retrieval_scoped_to_case(analyst_client, investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)

    summary = analyst_client.post(f"/api/v1/investigations/{investigation_id}/ai/summary").json()
    assert summary["provider"] == "DeterministicFallbackAIService"
    assert summary["grounded"] is True
    assert summary["content"]

    joined = " ".join(c["statement"] for c in summary["content"])
    # only this case's subject appears; unrelated athletes are never sent to the model
    assert "ATH-ALICE" in joined
    assert "ATH-CAROL" not in joined and "ATH-BOB" not in joined and "ATH-DAN" not in joined
    assert all(c["claim_type"] in {"RECORDED_FACT", "ANALYTICAL_SIGNAL", "INFERENCE", "INVESTIGATIVE_QUESTION"} for c in summary["content"])

    # gaps before evidence exists
    gaps = analyst_client.post(f"/api/v1/investigations/{investigation_id}/ai/information-gaps").json()
    gap_statements = " ".join(c["statement"] for c in gaps["content"])
    assert "no evidence items" in gap_statements

    # add case records, then re-draft: report must reference them
    evidence = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"title": "Lab record extract", "evidence_type": "DOCUMENT"},
    )
    assert evidence.status_code == 200
    finding = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={"title": "Preliminary assessment", "statement": "Continued review is warranted."},
    )
    assert finding.status_code == 200

    draft = analyst_client.post(f"/api/v1/investigations/{investigation_id}/ai/report-draft",
                                json={"purpose": "Review the analytical signals"}).json()
    assert draft["provider"] == "DeterministicFallbackAIService"
    sections = draft["draft"]["sections"]
    assert "Lab record extract" in sections["evidence"]
    assert any("Continued review is warranted" in f for f in sections["findings"])
    assert sections["case_metadata"]["subject"] == "ATHLETE Test ATH-ALICE"
    assert sections["purpose"] == "Review the analytical signals"


def test_ai_fallback_no_fiction_and_timeline(analyst_client, db):
    seed_domain(db)
    db.commit()
    direct = analyst_client.post(
        "/api/v1/investigations",
        json={"title": "No-alert case", "priority": "MODERATE",
              "subject_type": "ATHLETE", "subject_id": str(CAROL)},
    )
    assert direct.status_code == 200, direct.text
    investigation_id = direct.json()["id"]

    operations = [
        "summary",
        "timeline-summary",
        "signal-explanation",
        "information-gaps",
        "questions",
        "report-draft",
    ]
    blocks = []
    for operation in operations:
        body = {"signal_type": "RULE"} if operation == "signal-explanation" else None
        resp = analyst_client.post(f"/api/v1/investigations/{investigation_id}/ai/{operation}", json=body)
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["provider"] == "DeterministicFallbackAIService"
        assert payload["grounded"] is True
        blocks.append(payload)

    # deterministic fallback is labelled as such (the UI must not fake an LLM)
    # prohibited determinations never appear
    for block in blocks:
        for item in (block.get("content") or []):
            text = item["statement"].lower()
            assert not any(term in text for term in PROHIBITED), text

    # no data invented: case had no alert and no analytical signals
    summary = blocks[0]
    assert not any("originating alert" in c["statement"] for c in summary["content"])

    # signal explanation with a non-existent type reports the absence, grounded
    sig = blocks[2]
    assert any("No signals of type 'RULE'" in c["statement"] for c in sig["content"]) or \
           any("No analytical signals are linked to this case" in c["statement"] for c in sig["content"])


def test_reports_grounded_and_versioned(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)

    evidence_title = "Confidential interview transcript"
    finding_statement = "The recorded signals establish reasonable cause for continued investigation."
    assert investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"title": evidence_title, "evidence_type": "STATEMENT", "classification": "CONFIDENTIAL"},
    ).status_code == 200
    assert investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={"title": "Cause assessment", "statement": finding_statement, "confident": False},
    ).status_code == 200

    created = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports",
        json={"purpose": "Document the analytical and investigative review."},
    )
    assert created.status_code == 200, created.text
    report = created.json()
    assert report["status"] == "DRAFT"
    assert report["version"] == 1
    sections = report["sections"]
    assert sections["case_metadata"]["case_ref"].startswith("CASE-")
    assert sections["case_metadata"]["originating_alert"].startswith("ALERT-")
    assert evidence_title in sections["evidence"]
    assert any(finding_statement in f for f in sections["findings"])
    assert sections["audit_metadata"]["version"] == 1
    assert sections["outcome"] == "TBD - to be determined by the investigating officer."

    listing = investigator_client.get(f"/api/v1/investigations/{investigation_id}/reports").json()
    assert listing["count"] == 1
    report_id = listing["reports"][0]["id"]

    # publish -> FINAL
    published = investigator_client.post(f"/api/v1/investigations/{investigation_id}/reports/{report_id}/publish")
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "FINAL"

    # editing a FINAL report creates the next version and supersedes the old one
    revised = investigator_client.patch(
        f"/api/v1/investigations/{investigation_id}/reports/{report_id}",
        json={"purpose": "Revised purpose after legal review.", "outcome": "Referred to the disciplinary panel."},
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["version"] == 2
    assert revised.json()["status"] == "DRAFT"
    assert revised.json()["purpose"] == "Revised purpose after legal review."
    assert revised.json()["outcome"] == "Referred to the disciplinary panel."

    listing = investigator_client.get(f"/api/v1/investigations/{investigation_id}/reports").json()
    versions = {r["version"]: r["status"] for r in listing["reports"]}
    assert versions == {2: "DRAFT", 1: "SUPERSEDED"}

    # detail of the published/old version kept intact, audit events attached
    old = investigator_client.get(f"/api/v1/investigations/{investigation_id}/reports/{report_id}").json()
    assert old["status"] == "SUPERSEDED"
    assert old["sections"]["evidence"] == [evidence_title]
    assert {a["action"] for a in old["audit_events"]} >= {"REPORT_CREATED", "REPORT_PUBLISHED", "REPORT_VERSIONED"}


def test_restricted_ai_and_report_operations(client, analyst_client, investigator_client, viewer_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)

    # unauthenticated: blocked from AI and from report listing
    assert client.post(f"/api/v1/investigations/{investigation_id}/ai/summary").status_code == 401
    assert client.get(f"/api/v1/investigations/{investigation_id}/reports").status_code == 401

    # viewer may READ AI output (decision support is not write work)
    assert viewer_client.post(f"/api/v1/investigations/{investigation_id}/ai/summary").status_code == 200
    assert viewer_client.post(f"/api/v1/investigations/{investigation_id}/ai/report-draft").status_code == 200

    # analyst (INTELLIGENCE_ANALYST) lacks REPORTS_GENERATE: cannot create reports
    blocked = analyst_client.post(
        f"/api/v1/investigations/{investigation_id}/reports",
        json={"purpose": "should be blocked"},
    )
    assert blocked.status_code == 403

    # viewer lacks REPORTS_GENERATE as well
    assert viewer_client.post(
        f"/api/v1/investigations/{investigation_id}/reports",
        json={"purpose": "should be blocked"},
    ).status_code == 403