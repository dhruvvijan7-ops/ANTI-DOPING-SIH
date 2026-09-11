"""Content-first format detection.

The upload filename and the MIME header supplied by the client are NOT trusted
(conditions §597). Detection reads the actual bytes: magic signatures first,
then structural heuristics. Legacy XLS is recognized and rejected explicitly
rather than misparsed (condition §598).
"""
from __future__ import annotations

import io
import json
import zipfile

from app.importers.errors import (
    BadUploadSizeError,
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
    FORMAT_XLS,
    FORMAT_XLSX,
)

MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MiB (condition §739 size limits)
MAX_PASTE_BYTES = 5 * 1024 * 1024  # 5 MiB


def _looks_binary(data: bytes) -> bool:
    """Heuristic: NUL bytes or a cluster of control bytes indicate binary data."""
    if not data:
        return False
    if b"\x00" in data:
        return True
    control = sum(1 for b in data if b < 9 or b == 11 or b == 12 or 14 <= b < 32)
    return control > 5


def _decode(data: bytes) -> str | None:
    """Best-effort text decode with BOM handling; returns None when undecodable."""
    for enc in ("utf-8-sig", "utf-16-le", "utf-16-be"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    try:
        return data.decode("cp1252")
    except (UnicodeDecodeError, LookupError):
        return None


def _sniff_delimiter(text: str, sample_lines: list[str]) -> str | None:
    candidates = [",", "\t", ";", "|"]
    if len(sample_lines) < 1:
        return None
    header = sample_lines[0]
    if not header:
        return None
    counts = {c: header.count(c) for c in candidates}
    # column delimiters: at least one occurrence, and the top choice must be
    # consistent across the first rows.
    best = max(candidates, key=lambda c: counts[c])
    if counts[best] == 0:
        return None
    consistent = all(
        (line.count(best) >= counts[best] // 2 or counts[best] == 0) for line in sample_lines[1:3]
    )
    return best if consistent else None


def _looks_tabular(text: str, sample_lines: list[str]) -> bool:
    """CSV-ish content: a non-empty header line with a delimiter and body rows."""
    if len(sample_lines) < 1 or not sample_lines[0].strip():
        return False
    if _sniff_delimiter(text, sample_lines) is None:
        return False
    if len(sample_lines) > 1 and sample_lines[1].strip():
        return True
    return len(sample_lines) == 1


def detect_format(filename: str | None, data: bytes) -> str:
    """Return the detected format key for raw upload bytes.

    Raises EmptyPayloadError / UnsupportedFormatError when undetectable or empty.
    """
    if not data or not data.strip():
        raise EmptyPayloadError("The uploaded content is empty.")

    # --- binary magic signatures ------------------------------------------
    if data[:5] == b"%PDF-":
        return FORMAT_PDF

    if data[:4] == b"\x50\x4b\x03\x04":  # ZIP container: XLSX or DOCX
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
        except (zipfile.BadZipFile, OSError):
            raise UnsupportedFormatError("The file appears corrupted and could not be read.")
        if "xl/workbook.xml" in names and any(n.startswith("xl/") for n in names):
            return FORMAT_XLSX
        if "word/document.xml" in names and any(n.startswith("word/") for n in names):
            return FORMAT_DOCX
        raise UnsupportedFormatError("Unsupported ZIP content; expected an XLSX workbook or DOCX document.")

    # --- text-based formats ------------------------------------------------
    if _looks_binary(data):
        raise UnsupportedFormatError("The file appears to contain binary rather than text content.")
    text = _decode(data)
    if text is None:
        raise UnsupportedFormatError("The file encoding could not be determined.")
    stripped = text.strip()
    if not stripped:
        raise EmptyPayloadError("The uploaded content is empty.")

    if stripped[0] in "[{":
        try:
            json.loads(stripped)
            return FORMAT_JSON
        except ValueError:
            # Not valid JSON - fall through to tabular/free-text handling.
            pass

    sample_lines = [ln for ln in stripped.splitlines() if ln.strip()][:4]
    if _looks_tabular(text, sample_lines):
        delim = _sniff_delimiter(text, sample_lines)
        return FORMAT_TSV if delim == "\t" else FORMAT_CSV

    ext = (filename or "").rsplit(".", 1)[-1].lower() if filename and "." in filename else ""
    if ext == "xls":
        raise UnsupportedFormatError(
            "Legacy XLS workbooks are not supported. Convert the file to XLSX or CSV and upload again "
            "(the platform does not misparse legacy formats)."
        )
    return FORMAT_TXT


def enforce_size_limit(file_size: int, *, paste: bool = False) -> None:
    limit = MAX_PASTE_BYTES if paste else MAX_FILE_BYTES
    if file_size > limit:
        kind = "paste content" if paste else "file"
        raise BadUploadSizeError(f"The {kind} is too large ({file_size} bytes); the limit is {limit} bytes.")