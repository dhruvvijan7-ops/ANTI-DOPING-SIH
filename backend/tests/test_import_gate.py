"""Integration tests: Import gate (checkpoint 1005).

Covers the full import workflow end-to-end for CSV/JSON/XLSX/DOCX/PDF/TXT via
upload and paste: content-first format detection, preview, explicit column
mapping, row validation (no silent discards), exact-only entity matching,
dedupe (within import and against existing records), partial/atomic commit,
cancel, file-hash provenance, RBAC, size limits, malformed/corrupt inputs,
and path-traversal sanitization (conditions §11-§27, §281-§287, §596-§607,
§736-§742, §755; acceptance §461-§462).
"""
from __future__ import annotations

import io
import uuid

from sqlalchemy import select

from app.models.audit import AuditEvent
from tests.support_domain import ALICE, seed_domain

CSV_DATA = "\n".join(
    [
        "Title,Report Date,Athlete ID,Reliability,Category,Description",
        "Sample intelligence A,2024-05-01,ATH-ALICE,B,DOPING,First imported record.",
        "Second imported,2024-05-02,ATH-ALICE,B,DOPING,Another record.",
        "",
    ]
)


def _upload(client, content, filename="data.csv", ctype="text/csv", name=None):
    data = {"name": name} if name else {}
    return client.post("/api/v1/imports/upload", files={"file": (filename, content, ctype)}, data=data)


def _validate(client, import_id, mapping=None):
    if isinstance(mapping, dict) and ("mapping" in mapping or "sheet_name" in mapping):
        body = mapping
    else:
        body = {"mapping": mapping or {}}
    return client.post(f"/api/v1/imports/{import_id}/mapping", json=body)


def _commit(client, import_id, statuses=("READY",)):
    return client.post(f"/api/v1/imports/{import_id}/commit", json={"include_statuses": list(statuses)})


def _import_csv_full(client, content=CSV_DATA, filename="data.csv"):
    up = _upload(client, content, filename)
    assert up.status_code == 200, up.text
    imp = up.json()
    val = _validate(client, imp["id"])
    assert val.status_code == 200, val.text
    return imp, val.json()


def _import_and_commit(client, content=None, filename="data.csv", statuses=("READY",), mapping=None):
    content = content if content is not None else CSV_DATA
    imp, validated = _import_csv_full(client, content, filename)
    if mapping:
        val = _validate(client, imp["id"], mapping)
        assert val.status_code == 200, val.text
        validated = val.json()
    done = _commit(client, imp["id"], statuses)
    assert done.status_code == 200, done.text
    return imp, validated, done.json()


def _make_xlsx(sheets: dict[str, list[list]]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_docx(sections: list[tuple[str, list[str]]]) -> bytes:
    from docx import Document

    doc = Document()
    for heading, paragraphs in sections:
        if heading:
            doc.add_heading(heading, level=1)
        for text in paragraphs:
            doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_pdf(text: str) -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    return buf.getvalue()


def _make_blank_pdf() -> bytes:
    from pypdf import PdfWriter

    buf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buf)
    return buf.getvalue()


def _titles_for(client, subject_id: uuid.UUID) -> list[str]:
    listing = client.get("/api/v1/intelligence/reports", params={"subject_id": str(subject_id)})
    assert listing.status_code == 200, listing.text
    return [r["title"] for r in listing.json()["reports"]]


def _err(resp) -> str:
    body = resp.json()
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return body["error"].get("message") or ""
    return str(body)


# --- happy-path workflows --------------------------------------------------
def test_csv_upload_preview_validate_commit_with_provenance(investigator_client, db):
    seed_domain(db)
    db.commit()

    imp, validated = _import_csv_full(investigator_client)
    import_id = imp["id"]

    assert imp["format"] == "CSV"
    assert imp["status"] == "PARSED"
    assert imp["source_filename"] == "data.csv"
    assert len(imp["columns"]) == 6
    assert imp["inferred_types"]["Report Date"] == "DATE"
    assert imp["inferred_types"]["Athlete ID"] == "STRING"
    assert imp["column_mapping"]["Title"] == "title"
    assert imp["column_mapping"]["Report Date"] == "report_date"
    assert imp["column_mapping"]["Athlete ID"] == "athlete_ref"
    assert imp["column_mapping"]["Category"] == "info_category"
    assert len(imp["preview"]) == 2
    assert imp["summary"]["total"] == 2

    assert validated["status"] == "VALIDATED"
    summary = validated["summary"]
    assert summary["ready"] == 2 and summary["invalid"] == 0
    row = validated["preview"][0]
    assert row["status"] == "READY"
    assert row["entity_match"]["method"] == "EXACT_REF"
    assert row["entity_match"]["subject_type"] == "ATHLETE"
    assert row["entity_match"]["subject_id"] == str(ALICE)
    assert row["dedupe_key"]
    assert row["normalized"]["reliability"] == "B"
    assert row["normalized"]["report_date"] == "2024-05-01"
    assert row["normalized"]["info_category"] == "DOPING"

    done = _commit(investigator_client, import_id)
    assert done.status_code == 200, done.text
    committed = done.json()
    assert committed["status"] == "COMMITTED"
    assert committed["summary"]["imported"] == 2
    assert len(committed["summary"]["report_ids"]) == 2
    assert committed["summary"]["source"]["source_type"] == "USER_UPLOAD"

    titles = _titles_for(investigator_client, ALICE)
    assert "Sample intelligence A" in titles
    assert "Second imported" in titles

    # row-level provenance + dedupe key persisted on the imported rows
    rows = investigator_client.get(f"/api/v1/imports/{import_id}/rows", params={"status": "IMPORTED"}).json()["rows"]
    assert len(rows) == 2
    assert rows[0]["report_id"]
    assert rows[0]["dedupe_key"]

    audit = db.scalar(
        select(AuditEvent).where(
            AuditEvent.action == "DATA_IMPORT_COMMITTED",
            AuditEvent.entity_id == import_id,
        )
    )
    assert audit is not None and audit.metadata_json


def test_xlsx_sheet_selection_reparses_and_commits(investigator_client, db):
    seed_domain(db)
    db.commit()
    workbook = _make_xlsx(
        {
            "Summary": [
                ["Title", "Report Date", "Athlete ID", "Category"],
                ["Summary sheet only", "2024-06-01", "ATH-ALICE", "DOPING"],
            ],
            "Details": [
                ["Title", "Report Date", "Athlete ID", "Category"],
                ["Details sheet only", "2024-06-02", "ATH-ALICE", "DOPING"],
            ],
        }
    )
    up = _upload(investigator_client, workbook, filename="book.xlsx", ctype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert up.status_code == 200, up.text
    imp = up.json()
    assert imp["format"] == "XLSX"
    assert set(imp["sheets"]) == {"Summary", "Details"}
    assert imp["sheet_name"] == "Summary"

    val = _validate(investigator_client, imp["id"], {"sheet_name": "Details", "mapping": {}})
    assert val.status_code == 200, val.text
    assert val.json()["sheet_name"] == "Details"
    assert val.json()["preview"][0]["normalized"]["title"] == "Details sheet only"
    assert val.json()["summary"]["ready"] == 1

    done = _commit(investigator_client, imp["id"])
    assert done.status_code == 200, done.text
    assert "Details sheet only" in _titles_for(investigator_client, ALICE)


def test_json_paste_dedupe_within_import(investigator_client, db):
    seed_domain(db)
    db.commit()
    import json as _json

    content = _json.dumps([
        {"title": "Repeated note", "report_date": "2024-07-01", "athlete_ref": "ATH-ALICE", "info_category": "DOPING"},
        {"title": "Repeated note", "report_date": "2024-07-01", "athlete_ref": "ATH-ALICE", "info_category": "DOPING"},
        {"title": "Unique note", "report_date": "2024-07-02", "athlete_ref": "ATH-ALICE", "info_category": "GENERAL"},
    ])
    resp = investigator_client.post("/api/v1/imports/paste", json={"name": "json paste", "content": content})
    assert resp.status_code == 200, resp.text
    imp = resp.json()
    assert imp["format"] == "JSON"
    assert imp["source_kind"] == "PASTE"
    assert imp["summary"]["total"] == 3

    val = _validate(investigator_client, imp["id"])
    assert val.status_code == 200, val.text
    s = val.json()["summary"]
    assert s["duplicates"] == 1 and s["ready"] == 2

    done = _commit(investigator_client, imp["id"])
    assert done.status_code == 200, done.text
    assert done.json()["summary"]["imported"] == 2
    assert done.json()["status"] == "PARTIAL"  # duplicate row remains uncommitted


def test_duplicate_against_existing_import(investigator_client, db):
    seed_domain(db)
    db.commit()
    _import_and_commit(investigator_client)  # first import already committed

    imp, validated = _import_csv_full(investigator_client)
    assert validated["summary"]["duplicates"] == 2  # both rows match existing records

    done = _commit(investigator_client, imp["id"])
    assert done.status_code == 200, done.text
    assert done.json()["summary"]["imported"] == 0
    assert done.json()["status"] == "PARTIAL"


def test_invalid_rows_are_never_silently_discarded(investigator_client, db):
    seed_domain(db)
    db.commit()
    content = "\n".join(
        [
            "Title,Report Date,Athlete ID",
            "Valid row,2024-05-01,ATH-ALICE",
            ",2024-05-01,ATH-ALICE",  # missing title
            "Unknown athlete,2024-05-01,ATH-NOPE",  # unresolvable entity
        ]
    )
    imp, validated = _import_csv_full(investigator_client, content=content)
    assert validated["summary"]["ready"] == 1
    assert validated["summary"]["invalid"] == 2

    invalid = investigator_client.get(
        f"/api/v1/imports/{imp['id']}/rows", params={"status": "INVALID"}
    ).json()["rows"]
    assert len(invalid) == 2
    errors_by_row = {r["row_number"]: r["errors"] for r in invalid}
    assert any("title is required" in e for e in errors_by_row[2])
    assert any("ATH-NOPE" in e and "does not match" in e for e in errors_by_row[3])

    done = _commit(investigator_client, imp["id"])
    assert done.status_code == 200, done.text
    assert done.json()["summary"]["imported"] == 1
    assert done.json()["summary"]["rejected"] == 2
    assert done.json()["status"] == "PARTIAL"
    # invalid rows remain visible for the reviewer
    still = investigator_client.get(f"/api/v1/imports/{imp['id']}/rows", params={"status": "INVALID"}).json()["rows"]
    assert len(still) == 2


def test_docx_paragraph_import_with_review_commit(investigator_client, db):
    seed_domain(db)
    db.commit()
    docx = _make_docx([("First heading", ["Body one."]), ("Second heading", ["Body two."])])
    up = _upload(investigator_client, docx, filename="notes.docx", ctype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert up.status_code == 200, up.text
    imp = up.json()
    assert imp["format"] == "DOCX"
    assert imp["structure"] == "UNSTRUCTURED"
    assert set(imp["columns"]) == {"section", "content"}
    assert imp["summary"]["total"] == 2

    mapping = {"section": "title", "content": "description", "line": "_skip", "page": "_skip"}
    val = _validate(investigator_client, imp["id"], mapping={k: v for k, v in mapping.items() if k in imp["columns"]})
    assert val.status_code == 200, val.text
    assert val.json()["summary"]["ready"] == 0
    assert val.json()["summary"]["review"] == 2  # valid but unresolved entity

    done = _commit(investigator_client, imp["id"], statuses=("REVIEW",))
    assert done.status_code == 200, done.text
    assert done.json()["summary"]["imported"] == 2
    rep = investigator_client.get(f"/api/v1/imports/{imp['id']}/rows", params={"status": "IMPORTED"}).json()["rows"][0]
    assert rep["entity_match"] is None  # unanchored record, committed explicitly


def test_pdf_text_extracted_and_blank_pdf_rejected(investigator_client, db):
    seed_domain(db)
    db.commit()
    pdf = _make_pdf("Extracted intelligence text.")
    up = _upload(investigator_client, pdf, filename="notes.pdf", ctype="application/pdf")
    assert up.status_code == 200, up.text
    imp = up.json()
    assert imp["format"] == "PDF"
    assert imp["structure"] == "UNSTRUCTURED"
    assert imp["columns"] == ["page", "content"]
    assert imp["summary"]["total"] == 1
    assert imp["preview"][0]["original"]["content"] == "Extracted intelligence text."

    blank = _make_blank_pdf()
    rejected = _upload(investigator_client, blank, filename="scan.pdf", ctype="application/pdf")
    assert rejected.status_code == 400
    assert "OCR" in _err(rejected)


# --- format detection / security ------------------------------------------
def test_format_detection_is_content_based_not_extension(investigator_client, db):
    seed_domain(db)
    db.commit()
    imp, validated = _import_csv_full(
        investigator_client, content=CSV_DATA, filename="data.json"  # mislabeled extension
    )
    assert imp["format"] == "CSV"
    assert validated["summary"]["ready"] == 2


def test_legacy_xls_rejected_explicitly(investigator_client, db):
    up = _upload(investigator_client, b"hello world", filename="old.xls", ctype="application/vnd.ms-excel")
    assert up.status_code == 400
    assert "XLS" in _err(up)


def test_empty_and_corrupt_payloads_rejected(investigator_client, db):
    empty = _upload(investigator_client, b"", filename="empty.csv")
    assert empty.status_code == 400

    corrupt = _upload(investigator_client, b"\x00\x01\x02\x03\xff\xfe", filename="bad.csv")
    assert corrupt.status_code == 400

    truncated_zip = _upload(investigator_client, b"PK\x03\x04garbage-not-a-zip", filename="bad.xlsx")
    assert truncated_zip.status_code == 400


def test_filename_sanitization(investigator_client, db):
    up = _upload(investigator_client, CSV_DATA, filename="..\\..\\evil.csv")
    assert up.status_code == 200, up.text
    assert up.json()["source_filename"] == "evil.csv"


def test_oversize_paste_rejected(investigator_client, db):
    content = "a" * (5 * 1024 * 1024 + 1)
    resp = investigator_client.post("/api/v1/imports/paste", json={"name": "huge", "content": content})
    assert resp.status_code == 400
    assert "too large" in _err(resp).lower()


# --- state guards / RBAC ----------------------------------------------------
def test_state_guards_commit_mapping_cancel(investigator_client, db):
    seed_domain(db)
    db.commit()
    imp, _ = _import_csv_full(investigator_client)
    import_id = imp["id"]

    first = _commit(investigator_client, import_id, statuses=("READY",))
    assert first.status_code == 200 and first.json()["status"] == "COMMITTED"

    # commit again should fail (already committed)
    again = _commit(investigator_client, import_id)
    assert again.status_code == 409

    # mapping after commit forbidden
    remap = _validate(investigator_client, import_id)
    assert remap.status_code == 409

    # commit before mapping/validation -> forbidden (status still PARSED)
    premature = _upload(investigator_client, CSV_DATA)
    assert premature.status_code == 200
    premature_id = premature.json()["id"]
    assert _commit(investigator_client, premature_id).status_code == 409

    # cancel works pre-commit; then the import is locked
    cancel = investigator_client.post(f"/api/v1/imports/{premature_id}/cancel")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "CANCELED"
    assert _validate(investigator_client, premature_id).status_code == 409
    assert _commit(investigator_client, premature_id).status_code == 409


def test_imports_rbac(investigator_client, viewer_client, admin_client, client, db):
    seed_domain(db)
    db.commit()
    # unauthenticated read -> 401
    assert client.get("/api/v1/imports").status_code == 401

    # viewer can list (read) but cannot upload/validate/commit
    assert viewer_client.get("/api/v1/imports").status_code == 200
    assert viewer_client.post(
        "/api/v1/imports/upload", files={"file": ("v.csv", CSV_DATA, "text/csv")}
    ).status_code == 403

    imp, validated = _import_csv_full(admin_client)
    assert viewer_client.get(f"/api/v1/imports/{imp['id']}").status_code == 200
    viewer_commit = viewer_client.post(f"/api/v1/imports/{imp['id']}/commit", json={"include_statuses": ["READY"]})
    assert viewer_commit.status_code == 403
    # investigator lacks commit permission? it has it; check analyst can validate
    assert validated["status"] == "VALIDATED"


def test_rows_pagination_and_search(investigator_client, db):
    seed_domain(db)
    db.commit()
    imp, _ = _import_csv_full(investigator_client)
    import_id = imp["id"]

    page1 = investigator_client.get(f"/api/v1/imports/{import_id}/rows", params={"limit": 1, "offset": 0})
    assert page1.status_code == 200
    assert page1.json()["count"] == 2
    assert len(page1.json()["rows"]) == 1

    search = investigator_client.get(f"/api/v1/imports/{import_id}/rows", params={"q": "alice"})
    assert search.json()["count"] == 2

    ready = investigator_client.get(f"/api/v1/imports/{import_id}/rows", params={"status": "READY"})
    assert ready.json()["count"] == 2


def test_import_listing_and_upload_metadata(investigator_client, db):
    seed_domain(db)
    db.commit()
    import hashlib

    up = _upload(investigator_client, CSV_DATA, filename="meta.csv")
    assert up.status_code == 200
    imp = up.json()
    assert imp["file_hash"] == hashlib.sha256(CSV_DATA.encode()).hexdigest()
    assert imp["file_size"] == len(CSV_DATA.encode())
    assert imp["progress"] == 35

    listing = investigator_client.get("/api/v1/imports", params={"status": "PARSED", "q": "meta"}).json()
    assert any(i["id"] == imp["id"] for i in listing["imports"])


def test_paste_txt_auto_detected(investigator_client, db):
    seed_domain(db)
    db.commit()
    resp = investigator_client.post(
        "/api/v1/imports/paste",
        json={"name": "free text paste", "content": "Line one.\nLine two."},
    )
    assert resp.status_code == 200, resp.text
    imp = resp.json()
    assert imp["format"] == "TXT"
    assert imp["summary"]["total"] == 2
    assert imp["preview"][0]["original"]["line"] == 1