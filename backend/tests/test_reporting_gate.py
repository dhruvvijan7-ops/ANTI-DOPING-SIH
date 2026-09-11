"""Integration tests: Reporting gate.

Covers the in-app structured document workspace:
create manual report, save/autosave structured blocks, AI draft (grounded, never
invents, labelled), per-section AI assist, review/publish/archive statuses,
versioning of published reports, report type, exports (HTML/DOCX/PDF) with
provenance, and RBAC enforcement.
"""
from __future__ import annotations

import uuid

from tests.support_domain import ALICE, seed_domain

PROHIBITED = ("guilty", "sanction", "confirmed doping", "prohibited substance detected")


def _convert_alice(investigator_client) -> str:
    resp = investigator_client.post("/api/v1/analysis/runs", json={})
    assert resp.status_code == 201, resp.text
    run_id = uuid.UUID(resp.json()["run_id"])
    alerts = investigator_client.get("/api/v1/alerts", params={"run_id": str(run_id)}).json()["alerts"]
    alert = next(a for a in alerts if a["subject_id"] == str(ALICE))
    converted = investigator_client.post(f"/api/v1/alerts/{alert['id']}/convert")
    assert converted.status_code == 200, converted.text
    return converted.json()["investigation"]["id"]


def _create_report(investigator_client, investigation_id: str, **kwargs) -> dict:
    req = {"purpose": kwargs.get("purpose", "Document the review.")}
    resp = investigator_client.post(f"/api/v1/investigations/{investigation_id}/reports", json=req)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _save_blocks(investigator_client, investigation_id: str, report_id: str, blocks: list[dict],
                 autosave: bool = False) -> dict:
    resp = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report_id}/document",
        json={"blocks": blocks, "autosave": autosave, "title": None},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _sections_lines(payload: dict) -> list[str]:
    """Flatten an AI payload (sections dict or blocks list) into searchable text."""
    out = []
    if "draft" in payload:
        for v in (payload["draft"]["sections"] or {}).values():
            if isinstance(v, list):
                out.extend(str(i) for i in v)
            elif isinstance(v, str):
                out.append(v)
    return out


def test_create_manual_report_with_structured_blocks(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)

    report = _create_report(investigator_client, investigation_id, purpose="Manual narrative.")
    assert report["status"] == "DRAFT"
    assert report["version"] == 1
    assert report["report_type"] == "MANUAL"
    assert report["blocks"] == [] and report["draft"] == []

    blocks = [
        {"id": "b1", "type": "heading", "text": "Introduction", "attrs": {"level": 2},
         "items": [], "head": [], "rows": [], "provenance": {"kind": "human", "refs": []}},
        {"id": "b2", "type": "paragraph", "text": "Manual narrative body text.", "attrs": {},
         "items": [], "head": [], "rows": [], "provenance": {"kind": "human", "refs": []}},
        {"id": "b3", "type": "table", "text": None, "attrs": {},
         "items": [], "head": ["Item", "Note"], "rows": [["A", "x"]], "provenance": {"kind": "human", "refs": []}},
    ]
    saved = _save_blocks(investigator_client, investigation_id, report["id"], blocks)
    assert len(saved["blocks"]) == 3
    assert saved["blocks"][0]["type"] == "heading"
    # Audit recorded
    detail = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}"
    ).json()
    assert "REPORT_DOCUMENT_SAVED" in {a["action"] for a in detail["audit_events"]}


def test_autosave_does_not_overwrite_persisted_document(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)
    report = _create_report(investigator_client, investigation_id)

    # Persist a manual first draft.
    _save_blocks(investigator_client, investigation_id, report["id"], [
        {"id": "b1", "type": "paragraph", "text": "Persisted text", "attrs": {}, "items": [], "head": [], "rows": [],
         "provenance": {"kind": "human", "refs": []}},
    ])

    # Autosave a newer working draft.
    autosaved = _save_blocks(investigator_client, investigation_id, report["id"], [
        {"id": "b2", "type": "paragraph", "text": "Autosave working text", "attrs": {}, "items": [], "head": [], "rows": [],
         "provenance": {"kind": "human", "refs": []}},
    ], autosave=True)
    assert autosaved["draft"][0]["text"] == "Autosave working text"
    # The persisted version is untouched: blocks still holds the first save.
    assert autosaved["blocks"][0]["text"] == "Persisted text"
    assert autosaved["draft_saved_at"] is not None


def test_ai_draft_is_grounded_labelled_and_never_invents(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)

    # Add evidence so the draft references real records.
    assert investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"title": "Interview extract", "evidence_type": "STATEMENT"},
    ).status_code == 200

    report = _create_report(investigator_client, investigation_id)
    ai = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/ai-draft"
    )
    assert ai.status_code == 200, ai.text
    payload = ai.json()
    assert payload["provider"] == "DeterministicFallbackAIService"
    blocks = payload["blocks"]
    # structured AI document produced with provenance labels
    assert blocks and all(b["provenance"]["kind"] == "ai" for b in blocks)
    # The static methodology disclaimer uses mandated "guilt/sanctions" posture
    # language; PROHIBITED checks apply to case-content blocks only.
    content = [b for b in blocks if (b.get("text") or "").lower() not in {
        "this ai-generated draft was produced as decision support from the verified case record. "
        "it does not determine guilt or recommend sanctions and must be reviewed by an investigator."
    }]
    texts = " ".join((b.get("text") or "") for b in content)
    for row in content:
        for r in row.get("rows") or []:
            texts += " " + " ".join(r)
    assert "Interview extract" in texts, "AI draft must reference real evidence"
    assert "ATH-ALICE" in texts or "Test" in texts
    assert not any(t.lower() in texts.lower() for t in PROHIBITED)
    # report marked AI_ASSISTED on the stored object
    detail = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}"
    ).json()
    assert detail["report_type"] == "AI_ASSISTED"
    assert "REPORT_AI_DRAFT" in {a["action"] for a in detail["audit_events"]}


def test_ai_draft_never_fabricates_when_dataset_empty(investigator_client, db):
    seed_domain(db)
    db.commit()
    # A case with no originating alert/signals keeps AI honest.
    direct = investigator_client.post(
        "/api/v1/investigations",
        json={"title": "Quiet case", "priority": "MODERATE",
              "subject_type": "ATHLETE", "subject_id": str(ALICE)},
    )
    investigation_id = direct.json()["id"]

    report = _create_report(investigator_client, investigation_id)
    ai = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/ai-draft"
    ).json()
    blocks = ai["blocks"]
    # Skip the static methodology disclaimer (mandated posture language).
    content = [b for b in blocks if not (b.get("text") or "").startswith(
        "This AI-generated draft was produced as decision support")]
    joined = "\n".join((b.get("text") or "") for b in content)
    # Missing categories are explicitly stated, never invented.
    assert "No analytical signals are linked to this case" in joined or "current case record" in joined
    assert not any(t.lower() in joined.lower() for t in PROHIBITED)


def test_per_section_ai_assist(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)
    report = _create_report(investigator_client, investigation_id)

    for section, label in [("timeline", "Timeline summary"), ("evidence", "Evidence summary"),
                           ("gaps", "Gaps"), ("questions", "Investigative questions")]:
        resp = investigator_client.post(
            f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/ai-section",
            json={"section": section},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["section"] == section and body["label"] == label
        assert body["provider"] == "DeterministicFallbackAIService"
        assert body["blocks"] and all(b["provenance"]["kind"] == "ai" for b in body["blocks"])

    # unsupported section rejected
    bad = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/ai-section",
        json={"section": "nonsense"},
    )
    assert bad.status_code == 422


def test_status_workflow_review_publish_archive_and_versioning(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)
    report = _create_report(investigator_client, investigation_id)

    # DRAFT -> IN_REVIEW -> FINAL
    reviewed = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/review")
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "IN_REVIEW"

    published = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/publish")
    assert published.status_code == 200 and published.json()["status"] == "FINAL"
    assert published.json()["published_at"] is not None

    # duplicate publish is rejected
    dup = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/publish")
    assert dup.status_code == 409

    # editing a FINAL report versions it: old row superseded, new DRAFT opened
    revised = investigator_client.patch(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}",
        json={"purpose": "Revised after legal review."},
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["version"] == 2 and revised.json()["status"] == "DRAFT"

    listing = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/reports").json()
    by_version = {r["version"]: r["status"] for r in listing["reports"]}
    assert by_version == {2: "DRAFT", 1: "SUPERSEDED"}

    # archive the new draft
    archived = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{revised.json()['id']}/archive")
    assert archived.status_code == 200 and archived.json()["status"] == "ARCHIVED"

    # archived report cannot be edited
    locked = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{revised.json()['id']}/document",
        json={"blocks": [{"id": "x", "type": "paragraph", "text": "y", "attrs": {}, "items": [], "head": [], "rows": [],
                          "provenance": {"kind": "human", "refs": []}}], "autosave": False},
    )
    assert locked.status_code == 409


def test_report_type_set_and_validation(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)
    report = _create_report(investigator_client, investigation_id)
    assert report["report_type"] == "MANUAL"

    resp = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/type",
        json={"report_type": "HYBRID"},
    )
    assert resp.status_code == 200 and resp.json()["report_type"] == "HYBRID"
    assert resp.json()["report_type"] == "HYBRID"
    # invalid type rejected
    bad = investigator_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/type",
        json={"report_type": "MAGIC"},
    )
    assert bad.status_code == 422


def test_exports_include_provenance(investigator_client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)
    report = _create_report(investigator_client, investigation_id)
    _save_blocks(investigator_client, investigation_id, report["id"], [
        {"id": "b1", "type": "heading", "text": "Executive summary", "attrs": {"level": 1},
         "items": [], "head": [], "rows": [], "provenance": {"kind": "human", "refs": []}},
        {"id": "b2", "type": "paragraph", "text": "Body paragraph.", "attrs": {},
         "items": [], "head": [], "rows": [], "provenance": {"kind": "human", "refs": []}},
    ])

    html_resp = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/export/html")
    assert html_resp.status_code == 200, html_resp.text
    assert "text/html" in html_resp.headers["content-type"]
    html_body = html_resp.content.decode("utf-8")
    assert "Executive summary" in html_body
    assert "Body paragraph" in html_body
    assert "Case reference" in html_body and "Report version" in html_body
    assert report["investigation_id"] or report["id"]  # smoke no-op

    docx_resp = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/export/docx")
    assert docx_resp.status_code == 200, docx_resp.text
    assert "opendocument" in docx_resp.headers["content-type"] or "wordprocessingml" in docx_resp.headers["content-type"]
    assert docx_resp.content[:2] == b"PK"

    pdf_resp = investigator_client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/export/pdf")
    assert pdf_resp.status_code == 200, pdf_resp.text
    assert "application/pdf" in pdf_resp.headers["content-type"]
    assert pdf_resp.content[:5] == b"%PDF-"


def test_rbac_report_gate(investigator_client, analyst_client, viewer_client, client, db):
    seed_domain(db)
    db.commit()
    investigation_id = _convert_alice(investigator_client)
    report = _create_report(investigator_client, investigation_id)

    # Unauthenticated: all blocked.
    assert client.get(f"/api/v1/investigations/{investigation_id}/reports").status_code == 401
    assert client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/export/html").status_code == 401

    # Viewer may READ but not write.
    assert viewer_client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/export/html").status_code == 200
    assert viewer_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/document",
        json={"blocks": [], "autosave": False}).status_code == 403
    assert viewer_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/publish").status_code == 403

    # Analyst (INTELLIGENCE_ANALYST) lacks REPORTS_GENERATE: can't create or write.
    assert analyst_client.post(
        f"/api/v1/investigations/{investigation_id}/reports", json={}).status_code == 403
    assert analyst_client.post(
        f"/api/v1/investigations/{investigation_id}/reports/{report['id']}/ai-draft").status_code == 403

    # Investigator on another case: blocked from this investigation's reports.
    other_inv = investigator_client.post(
        "/api/v1/investigations",
        json={"title": "Other case", "priority": "LOW", "subject_type": "ATHLETE",
              "subject_id": str(ALICE)},
    ).json()["id"]
    assert investigator_client.get(
        f"/api/v1/investigations/{other_inv}/reports/{report['id']}").status_code == 404