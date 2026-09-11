"""Row validation, entity matching and dedupe (conditions §23-§26, §29).

Validation is row- and field-level; no row is silently discarded (§24).
Entity resolution is exact-match only — the platform never auto-approves a
fuzzy candidate (§26). Duplicate detection runs within the import and against
previously imported records via a normalized dedupe key.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.imports import (
    ROW_DUPLICATE,
    ROW_INVALID,
    ROW_READY,
    ROW_REVIEW,
    DataImport,
    ImportRow,
)
from app.models.intelligence import IntelligenceReport
from app.models.subjects import Athlete, Organization, Provider, SupportPerson, Team

# Normalized target fields a mapping may write to.
KNOWABLE_FIELDS = {
    "title",
    "description",
    "report_date",
    "reliability",
    "information_quality",
    "info_category",
    "confidentiality",
    "athlete_ref",
    "athlete_name",
    "support_ref",
    "support_name",
    "team_name",
    "organization_name",
    "provider_name",
    "external_ref",
    "source_ref",
}

VALID_RELIABILITY = {"A", "B", "C", "D"}
VALID_CONFIDENTIALITY = {"INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET", "TOP_SECRET", "CLASSIFIED"}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DT_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")

_WS = re.compile(r"\s+")


def infer_column_type(values: Iterable[object]) -> str:
    """Detect the dominant cell type for a column (condition §12 type detection)."""
    seen: set[str] = set()
    for v in values:
        if v is None or str(v).strip() == "":
            continue
        text = _to_str(v)
        key = _infer_single_type(text)
        seen.add(key)
    if not seen:
        return "STRING"
    ordered = ["DATE", "BOOLEAN", "NUMBER", "STRING"]
    return next(k for k in ordered if k in seen)


def _infer_single_type(text: str) -> str:
    if _ISO_DATE.match(text) or _DT_DATE.match(text):
        return "DATE"
    if text in {"true", "false"}:
        return "BOOLEAN"
    try:
        float(text)
        return "NUMBER"
    except ValueError:
        return "STRING"


def _to_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def normalize_dedupe_key(title: str, report_date: object, subject_key: str) -> str:
    norm_title = _WS.sub(" ", title.strip().lower())
    date_key = ""
    if isinstance(report_date, str):
        if _DT_DATE.match(report_date):
            report_date = report_date[:10]
        if _ISO_DATE.match(report_date):
            date_key = report_date
    elif isinstance(report_date, date):
        date_key = report_date.isoformat()
    parts = [p for p in (subject_key, norm_title, date_key) if p]
    return "|".join(parts) if parts else None


def _reliability(text: object) -> tuple[str | None, list[str], list[str]]:
    """Normalize reliability: strict on values, defaulted on blank (warn)."""
    errors: list[str] = []
    warnings: list[str] = []
    raw = _to_str(text).strip()
    if not raw:
        warnings.append("reliability was blank; defaulted to D (unevaluated).")
        return "D", errors, warnings
    val = raw.upper()
    if val not in VALID_RELIABILITY:
        errors.append(f"reliability {raw!r} is not one of A, B, C, D.")
        return raw, errors, warnings
    return val, errors, warnings


# --- subject resolution (exact match only) ---------------------------------
def _normalize(value: object) -> str:
    return _WS.sub(" ", _to_str(value).strip().lower())


def match_subject(db: Session, normalized: dict) -> tuple[dict | None, list[str]]:
    """Resolve the row entity. Returns (entity_match, error list).

    entity_match: {subject_type, subject_id, label, method}.
    method is EXACT_REF (platform external reference) or EXACT_NAME (exact
    normalized display-name match). No fuzzy/partial or automatic approval.
    """
    errors: list[str] = []
    ref_types = (
        ("ATHLETE", "athlete_ref", Athlete, "external_ref"),
        ("SUPPORT_PERSON", "support_ref", SupportPerson, "external_ref"),
    )
    for subject_type, field, model, attr in ref_types:
        ref = (normalized.get(field) or "").strip()
        if not ref:
            continue
        entity = db.scalar(select(model).where(getattr(model, attr) == ref))
        if entity is not None:
            sid = str(getattr(entity, "id"))
            label = getattr(entity, "last_name", None) or _to_str(getattr(entity, "name", "")) or ref
            return {"subject_type": subject_type, "subject_id": sid, "label": label, "method": "EXACT_REF"}, errors
        errors.append(f"{subject_type.lower()} reference {ref!r} does not match any known entity.")

    name_types = (
        ("ATHLETE", "athlete_name", Athlete, lambda e: f"{e.first_name} {e.last_name}".strip()),
        ("TEAM", "team_name", Team, lambda e: _to_str(e.name)),
        ("ORGANIZATION", "organization_name", Organization, lambda e: _to_str(e.name)),
        ("PROVIDER", "provider_name", Provider, lambda e: _to_str(e.name)),
        ("SUPPORT_PERSON", "support_name", SupportPerson, lambda e: _to_str(e.name)),
    )
    for subject_type, field, model, display in name_types:
        name = _normalize(normalized.get(field))
        if not name:
            continue
        entity = next(
            (e for e in db.scalars(select(model)).all() if _normalize(display(e)) == name),
            None,
        )
        if entity is not None:
            sid = str(getattr(entity, "id"))
            label = _to_str(display(entity))
            return {"subject_type": subject_type, "subject_id": sid, "label": label, "method": "EXACT_NAME"}, errors
        errors.append(f"{subject_type.lower()} name {name!r} does not match any known entity.")
    return None, errors


# --- row evaluation --------------------------------------------------------
def evaluate_row(db: Session, row: ImportRow, mapping: dict) -> dict:
    """Run validation + entity matching for a single row using import mapping.

    Returns the full verdict dict applied onto the row:
      {status, normalized, errors, warnings, entity_match, dedupe_key}
    """
    original = row.original or {}
    location = row.row_number
    normalized: dict = {}
    provenance: dict = {}
    for source_field, target_field in mapping.items():
        if not target_field or target_field == "_skip":
            continue
        normalized[target_field] = original.get(source_field)
        provenance[target_field] = {"original_field": source_field, "location": location}

    errors: list[str] = []
    warnings: list[str] = list(row.warnings or [])
    normalized = {k: _to_str(v) for k, v in normalized.items()}

    reliability, rel_errors, rel_warnings = _reliability(normalized.get("reliability"))
    normalized["reliability"] = reliability
    errors.extend(rel_errors)
    warnings.extend(rel_warnings)

    title = _WS.sub(" ", (normalized.get("title") or "").strip())
    if not title:
        errors.append("title is required.")
    else:
        if len(title) > 255:
            truncated = title[:255]
            warnings.append(f"title truncated from {len(title)} to 255 characters.")
            title = truncated
        normalized["title"] = title

    raw_date = normalized.get("report_date") or ""
    if raw_date:
        parsed = _parse_report_date(raw_date)
        if parsed is None:
            errors.append(f"report_date {raw_date!r} could not be parsed (use ISO YYYY-MM-DD).")
        else:
            normalized["report_date"] = parsed

    confidentiality = (normalized.get("confidentiality") or "INTERNAL").upper()
    if confidentiality not in VALID_CONFIDENTIALITY:
        warnings.append(f"confidentiality {confidentiality!r} unrecognized; defaulted to INTERNAL.")
        confidentiality = "INTERNAL"
    normalized["confidentiality"] = confidentiality

    for field, cap in (("description", 20000), ("info_category", 64), ("external_ref", 64)):
        value = _to_str(normalized.get(field)).strip()
        if value and len(value) > cap:
            warnings.append(f"{field} exceeds {cap} characters and was truncated.")
            value = value[:cap]
        normalized[field] = value if value else None
    info_quality = _to_str(normalized.get("information_quality")).strip().upper()
    if info_quality and info_quality not in {"1", "2", "3", "4"}:
        warnings.append(f"information_quality {info_quality!r} is unusual (expected 1-4); kept as-is.")
    normalized["information_quality"] = info_quality or None
    normalized["info_category"] = normalized.get("info_category") or "GENERAL"
    normalized["source_ref"] = _to_str(normalized.get("source_ref")).strip() or None

    entity_match, entity_errors = match_subject(db, normalized)
    row.entity_match = entity_match
    errors.extend(entity_errors)

    subject_key = ""
    if entity_match:
        subject_key = f"{entity_match['subject_type']}:{entity_match['subject_id']}"
    dedupe_key = normalize_dedupe_key(title, normalized.get("report_date"), subject_key)
    row.dedupe_key = dedupe_key

    status = ROW_INVALID if errors else (ROW_READY if entity_match else ROW_REVIEW)

    return {
        "status": status,
        "normalized": normalized,
        "errors": errors,
        "warnings": warnings,
        "entity_match": entity_match,
        "dedupe_key": dedupe_key,
        "provenance": provenance,
    }


def _parse_report_date(raw: str) -> str | None:
    """Parse a date cell into ISO YYYY-MM-DD."""
    from datetime import datetime

    text = raw.strip()
    if _ISO_DATE.match(text):
        return text
    if _DT_DATE.match(text):
        return text[:10]
    for fmt in ("%Y/%m/%d", "%d.%m.%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    # Day-first / month-first disambiguation: only unambiguous values accepted.
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", text):
        day, month, year = text.split("/")
        if int(day) > 12 and int(month) <= 12:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        if int(month) > 12 and int(day) <= 12:
            return f"{year}-{int(day):02d}-{int(month):02d}"
        if int(day) == int(month):
            return f"{year}-{int(month):02d}-{int(day):02d}"
        return None  # ambiguous MM/DD vs DD/MM -> explicit requirement
    return None


class DuplicateDetector:
    """Tracks dedupe keys within a single import and against existing records."""

    def __init__(self, db: Session, import_id) -> None:
        self.db = db
        self.import_id = import_id
        self._seen: set[str] = set()

    def classify(self, row: ImportRow) -> None:
        """Flag a row as DUPLICATE if its key repeats within this import or
        matches an already-imported record's dedupe key."""
        key = row.dedupe_key
        if not key:
            return
        if key in self._seen:
            row.status = ROW_DUPLICATE
            row.warnings = (row.warnings or []) + ["Duplicate of an earlier row within this import."]
            row.entity_match = None
            return
        existing = self.db.scalar(
            select(IntelligenceReport.id).where(
                IntelligenceReport.dedupe_key == key,
                IntelligenceReport.dedupe_key.isnot(None),
            )
        )
        self._seen.add(key)
        if existing is not None:
            row.status = ROW_DUPLICATE
            row.warnings = (row.warnings or []) + [
                f"Duplicate of existing intelligence record {existing}."
            ]
            row.entity_match = None

    def advance(self, key: str) -> None:
        self._seen.add(key)


def summarize(rows: list[ImportRow]) -> dict:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
    return {
        "total": len(rows),
        "ready": counts.get(ROW_READY, 0),
        "review": counts.get(ROW_REVIEW, 0),
        "duplicates": counts.get(ROW_DUPLICATE, 0),
        "invalid": counts.get(ROW_INVALID, 0),
        "imported": counts.get("IMPORTED", 0),
        "rejected": counts.get("REJECTED", 0),
    }


__all__ = [
    "DuplicateDetector",
    "KNOWABLE_FIELDS",
    "evaluate_row",
    "infer_column_type",
    "match_subject",
    "normalize_dedupe_key",
    "summarize",
]