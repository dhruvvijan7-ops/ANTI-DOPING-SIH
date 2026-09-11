"""Import pipeline package.

See VERITY master prompt §§11-27 (formats/workflow), §§281-287 (async/large
files/cancel/partial), §§596-607 (preview, explicit mapping, provenance),
§§736-742 (fixtures, malformed inputs, limits). Public surface:

    detect_format(filename, data) -> detected format
    parse_payload(name, data, filename=None, source_kind="FILE") -> ParsedTable
    apply_mapping_and_validate(db, import_ob) -> ValidationSummary
    commit_import(db, import_ob, include_statuses, user) -> CommitSummary
"""
from __future__ import annotations

from app.importers.detect import detect_format
from app.importers.parsers import parse_payload
from app.importers.pipeline import (
    apply_mapping_and_validate,
    commit_import,
    sanitize_filename,
    sha256,
    store_parsed_rows,
)
from app.importers.errors import (
    BadUploadError,
    EmptyPayloadError,
    UnsupportedFormatError,
)

__all__ = [
    "BadUploadError",
    "EmptyPayloadError",
    "UnsupportedFormatError",
    "apply_mapping_and_validate",
    "commit_import",
    "detect_format",
    "parse_payload",
    "sanitize_filename",
    "sha256",
]