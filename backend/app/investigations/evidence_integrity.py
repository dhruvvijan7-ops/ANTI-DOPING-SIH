"""Evidence content integrity (deterministic hash).

Every EvidenceItem stores a sha256 over the canonical, whitespace-normalized form
of its mutable content fields. The canonical form is documented so the hash is
reproducible independently of this codebase:

    prefix      = "clean-sport-evidence-v1"
    record      = "\x1f".join([prefix] + field values, with None -> "")
    canonical   = record.encode("utf-8")
    sha256      = hashlib.sha256(canonical).hexdigest()

Field order: title, description, evidence_type, source, classification,
sensitivity, item_date (UTC ISO 8601 when present), relationship_to_case.

The current row is always hashed over its CURRENT fields, so verifying an item
is simply recomputing and comparing. Old rows that predate integrity tracking
have sha256_hash = NULL and report verified=False.

This is deliberate: a real, documented hash rather than bespoke "tamper-evident"
crypto. See handover §19/§44.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

_CANONICAL_PREFIX = "clean-sport-evidence-v1"
_FIELD_ORDER = (
    "title",
    "description",
    "evidence_type",
    "source",
    "classification",
    "sensitivity",
    "item_date",
    "relationship_to_case",
)

FIELD_ORDER = _FIELD_ORDER


def canonicalize(fields: dict[str, Any]) -> bytes:
    """Build the canonical byte record for an evidence item's content fields."""
    parts = [_CANONICAL_PREFIX]
    for key in _FIELD_ORDER:
        value = fields.get(key)
        if value is None:
            parts.append("")
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            parts.append(value.astimezone(timezone.utc).isoformat())
        else:
            parts.append(str(value).strip())
    return "\x1f".join(parts).encode("utf-8")


def content_hash(fields: dict[str, Any]) -> str:
    """sha256 hex digest of the canonical record."""
    return hashlib.sha256(canonicalize(fields)).hexdigest()


def evidence_fields(item) -> dict[str, Any]:
    """Extract the mutable content fields used by the canonical hash from an
    EvidenceItem (SQLAlchemy row or a plain mapping)."""
    if hasattr(item, "_sa_instance_state"):
        return {key: getattr(item, key) for key in _FIELD_ORDER}
    return {key: item.get(key) for key in _FIELD_ORDER}