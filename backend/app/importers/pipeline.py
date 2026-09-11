"""Import pipeline orchestration: store parsed rows, validate, commit.

The pipeline is deterministic (no LLM in the loop). Failed commits are rolled
back atomically and surfaced with an explicit error (conditions §24, §602).
"""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.parsers import ParsedTable
from app.importers.validate import (
    KNOWABLE_FIELDS,
    DuplicateDetector,
    evaluate_row,
    infer_column_type,
    summarize,
)
from app.models.imports import (
    ROW_DUPLICATE,
    ROW_IMPORTED,
    ROW_INVALID,
    ROW_READY,
    ROW_REJECTED,
    ROW_REVIEW,
    STATUS_COMMITTED,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_PARSED,
    STATUS_UPLOADED,
    STATUS_VALIDATED,
    DataImport,
    ImportRow,
)
from app.models.intelligence import IntelligenceReport, IntelligenceSource

# Fields a mapped source column may write to.
MAPPABLE_FIELDS = KNOWABLE_FIELDS | {"_skip", ""}

_SYNONYMS: dict[str, set[str]] = {
    "title": {"title", "report title", "heading", "headline"},
    "report_date": {"report_date", "date", "report date", "event date", "observation date", "submitted on"},
    "description": {"description", "details", "summary", "content", "notes", "body", "intelligence", "text", "narrative"},
    "reliability": {"reliability"},
    "information_quality": {"information_quality", "quality", "information quality"},
    "info_category": {"info_category", "category", "type", "info category", "information category"},
    "confidentiality": {"confidentiality"},
    "athlete_ref": {"athlete_id", "athlete_ref", "athlete ref", "id", "ref", "external_ref", "external id", "subject_id", "subject ref", "athlete id"},
    "athlete_name": {"athlete_name", "athlete", "name", "full name", "subject_name", "subject name"},
    "external_ref": {"intel_ref", "report_ref", "record ref", "reference id"},
    "source_ref": {"source_ref", "reference", "source reference", "case ref"},
}

_UNSTRUCTURED_DEFAULT = {
    "content": "description",
    "contents": "description",
    "text": "description",
    "page": "_skip",
    "line": "_skip",
    "table": "_skip",
    "row": "_skip",
    "section": "_skip",
}

_NORMALIZE_COL = re.compile(r"[^a-z0-9]+")


def header_key(header: str) -> str:
    return _NORMALIZE_COL.sub(" ", header.strip().lower()).strip()


def default_mapping(columns: list[str]) -> dict:
    """Column-name -> target field mapping used as a starting point. The user can
    always override it; nothing is assumed without review (condition §599)."""
    out: dict = {}
    for col in columns:
        key = header_key(col)
        if key in _UNSTRUCTURED_DEFAULT and _UNSTRUCTURED_DEFAULT[key] in KNOWABLE_FIELDS:
            out[col] = _UNSTRUCTURED_DEFAULT[key]
            continue
        matched = next((field for field, syns in _SYNONYMS.items() if key in syns), None)
        if matched:
            out[col] = matched
    return out


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_filename(name: str | None) -> str:
    base = os.path.basename((name or "").replace("\\", "/"))
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return cleaned[:200] or "upload"


def store_parsed_rows(
    db: Session,
    import_ob: DataImport,
    parsed: ParsedTable,
    *,
    mapping: dict | None = None,
) -> None:
    """Replace parsed rows + metadata for an import (re-parse-safe)."""
    import_ob.format = parsed.format
    import_ob.columns = parsed.columns
    import_ob.sheets = parsed.sheets or []
    import_ob.sheet_name = parsed.sheet_name
    import_ob.structure = parsed.structure
    import_ob.inferred_types = {c: infer_column_type([r.get(c) for r in parsed.rows]) for c in parsed.columns}
    import_ob.summary = {"parsing_warnings": list(parsed.warnings or []), "total": len(parsed.rows)}
    import_ob.error_message = None
    import_ob.column_mapping = mapping if mapping is not None else default_mapping(parsed.columns)

    for row in list(import_ob.rows):
        db.delete(row)
    db.flush()

    for idx, record in enumerate(parsed.rows, start=1):
        db.add(
            ImportRow(
                import_id=import_ob.id,
                row_number=idx,
                status=ROW_READY,
                original=record,
                normalized={},
                errors=[],
                warnings=[],
                field_provenance={},
            )
        )
    import_ob.status = STATUS_PARSED
    import_ob.progress = 35


def apply_mapping_and_validate(
    db: Session,
    import_ob: DataImport,
    *,
    mapping: dict | None = None,
) -> dict:
    """Apply a column mapping (optional) and validate every row.

    Runs normalized-value computation, field validation, exact entity matching
    and dedupe. Returns the row-status summary (condition §23-§26).
    """
    if import_ob.status not in {STATUS_UPLOADED, STATUS_PARSED, STATUS_VALIDATED}:
        raise _NotReady(f"Import is not in a state that supports validation ({import_ob.status}).")

    if mapping is not None:
        columns = set(import_ob.columns or [])
        for source_field, target_field in mapping.items():
            if source_field not in columns:
                raise ValueError(f"Mapping references unknown column {source_field!r}.")
            if target_field not in MAPPABLE_FIELDS:
                raise ValueError(f"Mapping target {target_field!r} is not a supported field.")
        import_ob.column_mapping = mapping

    mapping = import_ob.column_mapping or default_mapping(import_ob.columns or [])
    rows = db.scalars(
        select(ImportRow).where(ImportRow.import_id == import_ob.id).order_by(ImportRow.row_number)
    ).all()

    detector = DuplicateDetector(db, import_ob.id)
    for row in rows:
        verdict = evaluate_row(db, row, mapping)
        row.status = verdict["status"]
        row.normalized = verdict["normalized"]
        row.errors = verdict["errors"]
        row.warnings = verdict["warnings"]
        row.entity_match = verdict["entity_match"]
        row.dedupe_key = verdict["dedupe_key"]
        row.field_provenance = verdict["provenance"]
        row.report_id = None
        if verdict["status"] != ROW_INVALID:
            detector.classify(row)

    db.flush()
    summary = summarize(rows)
    parsing_warnings = (import_ob.summary or {}).get("parsing_warnings") or []
    if parsing_warnings:
        summary["parsing_warnings"] = parsing_warnings
    import_ob.summary = summary
    import_ob.status = STATUS_VALIDATED
    import_ob.validated_at = datetime.now(timezone.utc)
    import_ob.progress = 72
    import_ob.error_message = None
    db.flush()
    return summary


def commit_import(
    db: Session,
    import_ob: DataImport,
    *,
    include_statuses: list[str],
    actor: uuid.UUID | None,
) -> dict:
    """Commit selected rows into intelligence reports.

    Only READY/REVIEW rows may be selected: an operator explicitly opts in, and
    anything not selected is left untouched (partial import, §284). The commit is
    atomic: any failure rolls back and marks the import FAILED.
    """
    if import_ob.status != STATUS_VALIDATED:
        raise ValueError("The import must be validated before it can be committed.")
    if import_ob.committed_at is not None:
        raise ValueError("This import has already been committed.")

    allowed = {ROW_READY, ROW_REVIEW}
    selected = list(dict.fromkeys(s.upper() for s in include_statuses)) or [ROW_READY]
    unknown = [s for s in selected if s not in allowed]
    if unknown:
        raise ValueError(f"Cannot commit rows with status {', '.join(unknown)}.")

    rows = db.scalars(
        select(ImportRow).where(ImportRow.import_id == import_ob.id).order_by(ImportRow.row_number)
    ).all()
    target_rows = [r for r in rows if r.status in selected]

    source = _ensure_user_upload_source(db, import_ob)

    imported_count = 0
    rejected_count = 0
    created_ids: list[str] = []
    for row in target_rows:
        cfg = row.normalized or {}
        subject_type = subject_id = None
        if row.entity_match:
            subject_type = row.entity_match.get("subject_type")
            subject_id = uuid.UUID(row.entity_match.get("subject_id"))
        report = IntelligenceReport(
            source_id=source.id,
            subject_type=subject_type,
            subject_id=subject_id,
            title=(cfg.get("title") or "").strip()[:255],
            description=cfg.get("description"),
            report_date=_as_date(cfg.get("report_date")),
            reliability=(cfg.get("reliability") or "D").upper()[:8],
            information_quality=(cfg.get("information_quality") or None),
            confidentiality=(cfg.get("confidentiality") or "INTERNAL").upper()[:32],
            status="NEW",
            info_category=(cfg.get("info_category") or "GENERAL").upper()[:64],
            is_duplicate=False,
            dedupe_key=row.dedupe_key,
            external_ref=cfg.get("external_ref"),
            created_by=actor,
        )
        db.add(report)
        db.flush()
        row.report_id = report.id
        row.status = ROW_IMPORTED
        imported_count += 1
        created_ids.append(str(report.id))

    for row in rows:
        if row.status == ROW_INVALID:
            rejected_count += 1

    try:
        db.flush()
    except Exception as exc:
        db.rollback()
        import_ob.status = STATUS_FAILED
        import_ob.error_message = f"Commit failed and was rolled back: {exc}"
        db.add(import_ob)
        db.commit()
        raise

    import_ob.committed_at = datetime.now(timezone.utc)
    import_ob.progress = 100
    summary = summarize(rows)
    summary["imported"] = imported_count
    summary["rejected"] = rejected_count
    summary["report_ids"] = created_ids
    summary["source"] = {
        "source_id": str(source.id),
        "source_type": source.source_type,
        "name": source.name,
    }
    import_ob.summary = summary
    remaining = [r for r in rows if r.status in {ROW_INVALID, ROW_REVIEW, ROW_DUPLICATE, ROW_READY}]
    import_ob.status = STATUS_PARTIAL if remaining else STATUS_COMMITTED
    db.flush()
    return summary


def _ensure_user_upload_source(db: Session, import_ob: DataImport) -> IntelligenceSource:
    """Get-or-create the authoritative source record for a bulk import."""
    label = import_ob.source_filename or f"Paste import: {import_ob.name}"
    existing = db.scalar(
        select(IntelligenceSource).where(
            IntelligenceSource.source_type == "USER_UPLOAD",
            IntelligenceSource.name == label,
            IntelligenceSource.is_active.is_(True),
        )
    )
    if existing is not None:
        return existing
    source = IntelligenceSource(
        external_ref=f"IMPORT-{import_ob.id}",
        name=label,
        source_type="USER_UPLOAD",
        reliability_default="D",
        confidentiality="INTERNAL",
        activity=True,
        is_active=True,
    )
    db.add(source)
    db.flush()
    return source


def _as_date(value: object):
    from datetime import date

    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return value[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", value) else None
    return None


class _NotReady(Exception):
    pass


__all__ = [
    "MAPPABLE_FIELDS",
    "apply_mapping_and_validate",
    "commit_import",
    "default_mapping",
    "sanitize_filename",
    "sha256",
    "store_parsed_rows",
]