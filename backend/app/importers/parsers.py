"""Format parsers producing a normalized ParsedTable.

Parsers keep original cell values untouched (JSON-able scalars) and attach a
per-row provenance location (sheet / page / heading) that flows into the
field-level provenance used on commit (conditions §18, §603-§607).
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from app.importers.detect import MAX_FILE_BYTES, _decode, _sniff_delimiter
from app.importers.errors import (
    BadUploadError,
    EmptyPayloadError,
    UnsupportedFormatError,
)
from app.models.imports import (
    FORMAT_CSV,
    FORMAT_DOCX,
    FORMAT_JSON,
    FORMAT_PDF,
    FORMAT_TSV,
    FORMAT_TXT,
    FORMAT_XLSX,
)

STRUCTURE_TABULAR = "TABULAR"
STRUCTURE_UNSTRUCTURED = "UNSTRUCTURED"


@dataclass
class ParsedTable:
    format: str
    columns: list[str]
    rows: list[dict] = field(default_factory=list)
    sheet_name: str | None = None
    sheets: list[str] = field(default_factory=list)
    row_provenance: list[str | None] = field(default_factory=list)
    structure: str = STRUCTURE_TABULAR
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)


def _clean_header(value: object, idx: int) -> str:
    text = _to_text(value).strip()
    return text if text else f"column_{idx + 1}"


def _to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _cell(value: object) -> object:
    """JSON-serializable scalar for original row values."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _to_text(value)


def parse_payload(
    payload: bytes,
    *,
    format_key: str,
    filename: str | None = None,
    sheet_name: str | None = None,
) -> ParsedTable:
    """Dispatch to the appropriate parser for the detected format key."""
    if format_key == FORMAT_CSV:
        return _parse_csv(payload, "\t" if False else None, tsv=False)
    if format_key == FORMAT_TSV:
        return _parse_csv(payload, "\t", tsv=True)
    if format_key == FORMAT_JSON:
        return _parse_json(payload)
    if format_key == FORMAT_XLSX:
        return _parse_xlsx(payload, sheet_name=sheet_name)
    if format_key == FORMAT_DOCX:
        return _parse_docx(payload)
    if format_key == FORMAT_PDF:
        return _parse_pdf(payload)
    if format_key == FORMAT_TXT:
        return _parse_txt(payload)
    raise UnsupportedFormatError(f"Unsupported import format: {format_key}")


# --- CSV / TSV -------------------------------------------------------------
def _parse_csv(payload: bytes, forced_delimiter: str | None, *, tsv: bool) -> ParsedTable:
    text = _decode(payload)
    if text is None:
        raise BadUploadError("The CSV content could not be decoded.")
    warnings: list[str] = []
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
        warnings.append("UTF-8 BOM removed.")
    text = text.strip()
    if not text:
        raise EmptyPayloadError("The CSV content is empty.")
    if "\x00" in text:
        raise BadUploadError("The file appears to contain binary data rather than CSV text.")

    sample_lines = [ln for ln in text.splitlines() if ln.strip()][:4]
    delimiter = forced_delimiter
    if delimiter is None:
        delimiter = _sniff_delimiter(text, sample_lines) or ","
        if delimiter != ",":
            warnings.append(f"Delimiter {delimiter!r} detected.")

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        first = next(reader)
    except (csv.Error, StopIteration):
        raise EmptyPayloadError("The CSV content could not be parsed.")
    first = [_clean_header(v, i) for i, v in enumerate(first)]
    columns = list(dict.fromkeys(first))
    if len(columns) != len(first):
        warnings.append("Duplicate column headers were renamed.")
    effective = [c if c in columns else f"column_{i + 1}" for i, c in enumerate(first)]

    rows: list[dict] = []
    loc: list[str | None] = []
    row_no = 1
    for line in reader:
        row_no += 1
        if not any((str(v).strip()) for v in line):
            continue  # fully blank lines ignored
        record: dict[str, object] = {}
        for i, col in enumerate(effective):
            record[col] = _cell(line[i]) if i < len(line) else ""
        rows.append(record)
        loc.append(f"row {row_no}")
    if not rows:
        warnings.append("The file contains headers but no data rows.")
    return ParsedTable(
        format=FORMAT_TSV if tsv else FORMAT_CSV,
        columns=columns,
        rows=rows,
        row_provenance=loc,
        structure=STRUCTURE_TABULAR,
        warnings=warnings,
        info={"delimiter": delimiter},
    )


# --- JSON ------------------------------------------------------------------
def _parse_json(payload: bytes) -> ParsedTable:
    text = _decode(payload)
    if text is None:
        raise BadUploadError("The JSON content could not be decoded.")
    text = text.strip()
    if not text:
        raise EmptyPayloadError("The JSON content is empty.")
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise BadUploadError(f"The JSON content is malformed: {exc}")

    warnings: list[str] = []
    if isinstance(data, dict):
        for key in ("data", "records", "items", "rows", "intelligence"):
            value = data.get(key)
            if isinstance(value, list):
                if value or all(isinstance(v, dict) for v in value):
                    data = value
                    warnings.append(f"Wrapped list extracted from the {key!r} field.")
                    break
        if isinstance(data, dict):
            data = [data]
    if not isinstance(data, list):
        raise BadUploadError("The JSON content must be an object array (or a single object).")

    records: list[dict] = []
    for item in data:
        if isinstance(item, dict):
            records.append(_flatten(item))
        elif isinstance(item, (str, int, float, bool)) or item is None:
            records.append({"value": item})
        else:
            raise BadUploadError("Each JSON element must be an object.")
    if not records:
        raise EmptyPayloadError("The JSON content contains no records.")

    columns = list(dict.fromkeys(k for r in records for k in r.keys()))
    rows = [{c: _cell(r.get(c)) for c in columns} for r in records]
    loc = [None] * len(rows)
    return ParsedTable(
        format=FORMAT_JSON,
        columns=columns,
        rows=rows,
        row_provenance=loc,
        structure=STRUCTURE_TABULAR,
        warnings=warnings,
        info={"records": len(records)},
    )


def _flatten(obj: dict, prefix: str = "") -> dict:
    out: dict = {}
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(_flatten(value, path))
        else:
            out[path] = value
    return out


# --- XLSX ------------------------------------------------------------------
def _parse_xlsx(payload: bytes, *, sheet_name: str | None = None) -> ParsedTable:
    try:
        from openpyxl import load_workbook
    except ImportError:  # pragma: no cover - guarded by deployment deps
        raise BadUploadError("XLSX support is unavailable on this deployment.")
    try:
        wb = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as exc:
        raise BadUploadError(f"The XLSX workbook could not be read: {exc}")
    sheet_names = wb.sheetnames
    if not sheet_names:
        raise EmptyPayloadError("The workbook contains no sheets.")
    selected = sheet_name if sheet_name in sheet_names else sheet_names[0]
    ws = wb[selected]

    warnings: list[str] = []
    header: list[str | None] | None = None
    rows: list[dict] = []
    loc: list[str | None] = []
    for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if row is None:
            continue
        values = list(row)
        if not any(v is not None and str(v).strip() for v in values):
            continue
        if header is None:
            header = [_clean_header(v, i) for i, v in enumerate(values)]
            columns = list(dict.fromkeys(h for h in header))
            if len(columns) != len(header):
                warnings.append("Duplicate column headers were renamed.")
            effective = [c if c in columns else f"column_{i + 1}" for i, c in enumerate(header)]
            continue
        record = {effective[i]: _cell(values[i]) if i < len(values) else "" for i in range(len(effective))}
        rows.append(record)
        loc.append(f"sheet {selected!r}, row {r_idx + 1}")
    if header is None or not rows:
        warnings.append("The selected sheet has headers but no data rows.")
    wb.close()
    columns = list(dict.fromkeys(h for h in header)) if header else []
    if not columns and rows:
        columns = sorted(rows[0].keys())
    return ParsedTable(
        format=FORMAT_XLSX,
        columns=columns,
        rows=rows,
        sheet_name=selected,
        sheets=sheet_names,
        row_provenance=loc,
        structure=STRUCTURE_TABULAR,
        warnings=warnings,
        info={"workbook_sheets": sheet_names},
    )


# --- DOCX ------------------------------------------------------------------
_HEADING_RE = re.compile(r"^H([1-6])$", re.IGNORECASE)


def _parse_docx(payload: bytes) -> ParsedTable:
    try:
        from docx import Document
    except ImportError:  # pragma: no cover - guarded by deployment deps
        raise BadUploadError("DOCX support is unavailable on this deployment.")
    try:
        document = Document(io.BytesIO(payload))
    except Exception as exc:
        raise BadUploadError(f"The DOCX document could not be read: {exc}")

    warnings: list[str] = []

    table_rows: list[dict] = []
    for table_idx, table in enumerate(document.tables, start=1):
        for tbl_idx, row in enumerate(table.rows):
            cells = [_cell(c.text) for c in row.cells]
            if tbl_idx == 0:
                continue  # header row
            if not any(str(c).strip() for c in cells):
                continue
            table_rows.append(
                {"table": str(table_idx), "row": str(tbl_idx + 1), "cells": " | ".join(str(c) for c in cells)}
            )

    paragraphs: list[tuple[str, str]] = []
    current_heading = None
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = para.style.name if para.style else ""
        m = _HEADING_RE.match(style)
        if m or "Heading" in style or para.style.style_id == "Heading1":
            current_heading = text
            continue
        paragraphs.append((current_heading or "", text))
    if current_heading is not None and not paragraphs:
        warnings.append("Document contains headings but no body text.")

    if table_rows:
        columns = ["table", "row", "cells"]
        rows = table_rows
        structure = STRUCTURE_TABULAR
        loc = [f"table {r['table']}, row {r['row']}" for r in rows]
        warnings.append("Tabular content extracted from document tables.")
    elif paragraphs:
        columns = ["section", "content"]
        rows = [{"section": sec if sec else "", "content": txt} for sec, txt in paragraphs]
        structure = STRUCTURE_UNSTRUCTURED
        loc = [f"section {sec!r}" if sec else None for sec, _ in paragraphs]
        warnings.append("Paragraph content extracted; nearest heading recorded as section.")
    else:
        raise EmptyPayloadError("The DOCX document contains no extractable content.")

    return ParsedTable(
        format=FORMAT_DOCX,
        columns=columns,
        rows=rows,
        row_provenance=loc,
        structure=structure,
        warnings=warnings,
        info={"paragraphs": len(paragraphs), "tables": len(document.tables)},
    )


# --- PDF -------------------------------------------------------------------
def _parse_pdf(payload: bytes) -> ParsedTable:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - guarded by deployment deps
        raise BadUploadError("PDF support is unavailable on this deployment.")
    try:
        reader = PdfReader(io.BytesIO(payload))
    except Exception as exc:
        raise BadUploadError(f"The PDF could not be read: {exc}")
    if reader.is_encrypted:
        raise BadUploadError("The PDF is password protected and cannot be read.")
    if len(reader.pages) == 0:
        raise EmptyPayloadError("The PDF contains no pages.")

    rows: list[dict] = []
    loc: list[str | None] = []
    for page_idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            rows.append({"page": page_idx, "content": text})
            loc.append(f"page {page_idx}")
    if not rows:
        raise BadUploadError(
            "The PDF contains no embedded text; scanning/OCR is not supported by this import path. "
            "Provide a text-based PDF or convert to CSV/JSON."
        )
    return ParsedTable(
        format=FORMAT_PDF,
        columns=["page", "content"],
        rows=rows,
        row_provenance=loc,
        structure=STRUCTURE_UNSTRUCTURED,
        warnings=["PDF text was extracted as-is; layout fidelity is not guaranteed."],
        info={"pages": len(reader.pages)},
    )


# --- TXT / paste -----------------------------------------------------------
def _parse_txt(payload: bytes) -> ParsedTable:
    text = _decode(payload)
    if text is None:
        raise BadUploadError("The text content could not be decoded.")
    text = text.replace("\ufeff", "").strip()
    if not text:
        raise EmptyPayloadError("The text content is empty.")
    lines = text.splitlines()

    sample_lines = [ln for ln in lines if ln.strip()][:4]
    delimiter = _sniff_delimiter(text, sample_lines)
    if delimiter:
        return _parse_csv(payload, delimiter, tsv=delimiter == "\t")

    rows = [{"line": i + 1, "content": ln.strip()} for i, ln in enumerate(lines) if ln.strip()]
    loc = [f"line {i + 1}" for i, ln in enumerate(lines) if ln.strip()]
    return ParsedTable(
        format=FORMAT_TXT,
        columns=["line", "content"],
        rows=rows,
        row_provenance=loc,
        structure=STRUCTURE_UNSTRUCTURED,
        info={"lines": len(rows)},
    )


__all__ = [
    "MAX_FILE_BYTES",
    "ParsedTable",
    "STRUCTURE_TABULAR",
    "STRUCTURE_UNSTRUCTURED",
    "parse_payload",
]