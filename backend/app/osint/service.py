"""OSINT collection, dedupe, entity linking, promotion and claims (gate 1006).

Design notes:
- Collection is always targeted; neutral (feed/page) sources are post-filtered by
  the requested terms when provided (gate §243).
- Records are stored with full provenance even when flagged as duplicates, so the
  raw record remains traceable (gate §49-§51).
- Source health is updated on every run: ACTIVE/DEGRADED/FAILED/RATE_LIMITED (§48).
- Promote -> IntelligenceReport keeps the OSINT provenance columns so the record
  can be traced back to its raw OSINT row and its original external URL (§735).
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intelligence import IntelligenceReport, IntelligenceSource
from app.models.identity import User
from app.models.osint import (
    DUP_CANONICAL_URL,
    DUP_CONTENT_HASH,
    HEALTH_ACTIVE,
    HEALTH_DEGRADED,
    HEALTH_DISABLED,
    HEALTH_FAILED,
    HEALTH_RATE_LIMITED,
    OsintClaim,
    OsintMention,
    OsintRecord,
    OsintSource,
    published_date_of,
)
from app.models.subjects import Athlete, Organization, SupportPerson, Team
from app.osint.common import (
    HttpStatusError,
    InvalidSourceUrlError,
    RateLimitedError,
    acquire_slot,
    content_hash,
    parse_datetime,
    title_signature,
)
from app.osint.connectors.base import CollectionQuery, ConnectorError, RawItem
from app.osint.connectors.registry import get_connector

logger = logging.getLogger("clean_sport.osint")

# Connector kinds that perform server-side search and therefore need no
# post-filtering (their results already match the requested terms).
_SEARCH_CONNECTORS = {"gdelt"}

# Enum maps
_AUTHORITY_RELIABILITY = {
    "OFFICIAL": "B",
    "PUBLIC_NEWS": "C",
    "PUBLIC_SOCIAL": "D",
    "ARCHIVAL": "C",
    "COMMERCIAL": "C",
}


# ---------------------------------------------------------------------------
# Health bookkeeping
# ---------------------------------------------------------------------------

def _mark_disabled(source: OsintSource) -> None:
    source.health = HEALTH_DISABLED
    source.consecutive_failures += 1


def _mark_failure(source: OsintSource, reason: str, *, rate_limited: bool = False) -> None:
    now = datetime.now(timezone.utc)
    source.health = HEALTH_RATE_LIMITED if rate_limited else HEALTH_FAILED
    source.consecutive_failures += 1
    source.last_failure_at = now
    source.last_failure_reason = reason[:4000]
    logger.warning("OSINT source %s failed: %s", source.source_id, reason)


def _mark_success(source: OsintSource) -> None:
    now = datetime.now(timezone.utc)
    # A clean run after one or more failures reports DEGRADED (recovering), then a
    # subsequent clean run returns to ACTIVE.
    if source.consecutive_failures > 0:
        source.health = HEALTH_DEGRADED
        source.consecutive_failures = 0
    else:
        source.health = HEALTH_ACTIVE
    source.last_failure_reason = None
    source.last_success_at = now


def _fetch_items(source: OsintSource, query: CollectionQuery) -> list[RawItem]:
    """Dispatch to the registered connector, translating transport failures into
    typed exceptions the caller maps to health states."""
    connector_cls = get_connector(source.connector_type)
    if connector_cls is None:
        raise ConnectorError(
            f"No connector registered for type {source.connector_type!r}"
        )
    connector = connector_cls()
    try:
        return connector.fetch(source, query)
    except (InvalidSourceUrlError, RateLimitedError, HttpStatusError, ConnectorError):
        raise
    except httpx.TimeoutException as exc:
        raise ConnectorError(f"Upstream timeout fetching {source.url}") from exc
    except Exception as exc:  # noqa: BLE001 - connector boundary
        raise ConnectorError(f"Connector error: {exc}") from exc


# ---------------------------------------------------------------------------
# Dedupe / syndication
# ---------------------------------------------------------------------------

def _dedupe_target(db: Session, fpr: str, canonical_url: str | None) -> tuple[uuid.UUID | None, str | None]:
    """Return (existing_record_id, reason) or (None, None) when this is a new record."""
    by_hash = db.scalar(select(OsintRecord).where(OsintRecord.content_hash == fpr))
    if by_hash is not None:
        return by_hash.id, DUP_CONTENT_HASH
    if canonical_url:
        by_url = db.scalar(select(OsintRecord).where(OsintRecord.canonical_url == canonical_url))
        if by_url is not None:
            return by_url.id, DUP_CANONICAL_URL
    return None, None


def _syndication_key(db: Session, signature: str) -> str:
    """Return an existing syndication group key or create a fresh one."""
    existing = db.scalar(
        select(OsintRecord.syndication_group).where(
            OsintRecord.syndication_group.isnot(None),
            OsintRecord.syndication_group.ilike(f"{signature}%"),
        ).limit(1)
    )
    if existing:
        return existing
    return f"{signature}-{uuid.uuid4().hex[:8]}"[:64]


def _terms_tokens(terms: str | None) -> list[str]:
    if not terms:
        return []
    return [t.lower() for t in terms.replace(",", " ").split() if len(t.strip()) > 1]


def _record_matches_terms(item: RawItem, tokens: list[str]) -> bool:
    if not tokens:
        return True
    haystack = f"{(item.title or '')} {(item.content or '')}".lower()
    return any(t in haystack for t in tokens)


# ---------------------------------------------------------------------------
# Entity mention extraction (grounded to DB subject rows)
# ---------------------------------------------------------------------------

def _subject_names(db: Session) -> list[tuple[str, uuid.UUID, str]]:
    """Load a bounded set of known entities to link mentions against."""
    found: list[tuple[str, uuid.UUID, str]] = []
    for model, subject_type, name_attr in (
        (Athlete, "ATHLETE", "full_name"),
        (SupportPerson, "SUPPORT_PERSON", "name"),
        (Team, "TEAM", "name"),
        (Organization, "ORGANIZATION", "name"),
    ):
        rows = db.scalars(
            select(model).where(model.status == "ACTIVE").limit(2000)
        ).all()
        for row in rows:
            label = (
                f"{row.first_name} {row.last_name}".strip()
                if subject_type == "ATHLETE"
                else getattr(row, name_attr, None)
            )
            if label and len(label) >= 3:
                found.append((subject_type, row.id, label))
    return found


def _extract_mentions(db: Session, record: OsintRecord, haystack: str) -> int:
    hay = (haystack or "").lower()
    count = 0
    for subject_type, subject_id, label in _subject_names(db):
        low = label.lower()
        if len(low) < 3 or low not in hay:
            continue
        existing = db.scalar(
            select(OsintMention).where(
                OsintMention.record_id == record.id,
                OsintMention.subject_type == subject_type,
                OsintMention.subject_id == subject_id,
            )
        )
        if existing is not None:
            continue
        match_kind = "EXACT" if _is_exact_mention(hay, low) else "CONTAINS"
        db.add(OsintMention(
            record_id=record.id,
            subject_type=subject_type,
            subject_id=subject_id,
            subject_label=label,
            match_kind=match_kind,
        ))
        count += 1
    return count


def _is_exact_mention(hay: str, needle: str) -> bool:
    import re

    return re.search(rf"(^|[\s.,;:!?\"'()\-]){re.escape(needle)}(?=$|[\s.,;:!?\"'()\-])", hay, re.IGNORECASE) is not None


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

def run_source_collection(
    db: Session,
    source: OsintSource,
    *,
    terms: str | None = None,
    days: int | None = None,
    max_records: int = 30,
) -> dict[str, Any]:
    """Collect one source and persist normalized records. Never raises for
    upstream failures — health is recorded and returned in the summary."""
    started = time.monotonic()
    query = CollectionQuery(
        terms=terms,
        days=days,
        max_records=max(1, min(max_records or 30, 100)),
    )
    summary: dict[str, Any] = {
        "source_id": source.source_id,
        "source_name": source.name,
        "health": source.health,
        "ok": False,
        "error": None,
        "new_records": 0,
        "duplicates": 0,
        "mentions": 0,
        "stored": [],
    }

    if not source.enabled:
        _mark_disabled(source)
        db.commit()
        summary.update(health=source.health, error="Source is disabled")
        return summary

    try:
        acquire_slot(source.id, source.rate_limit_per_min)
    except RateLimitedError as exc:
        _mark_failure(source, str(exc), rate_limited=True)
        db.commit()
        summary.update(health=source.health, error=str(exc), ok=False)
        return summary

    try:
        items = _fetch_items(source, query)
    except RateLimitedError as exc:
        _mark_failure(source, str(exc), rate_limited=True)
        db.commit()
        summary.update(health=source.health, error=str(exc))
        return summary
    except InvalidSourceUrlError as exc:
        reason = f"Invalid source URL: {exc}"
        _mark_failure(source, reason)
        db.commit()
        summary.update(health=source.health, error=reason)
        return summary
    except HttpStatusError as exc:
        reason = f"Upstream HTTP {exc.status_code}"
        if exc.status_code == 404:
            reason = "Source URL returned 404 Not Found"
        _mark_failure(source, reason, rate_limited=exc.is_rate_limited)
        db.commit()
        summary.update(health=source.health, error=reason)
        return summary
    except Exception as exc:  # noqa: BLE001 - connector boundary
        reason = f"{exc}"
        _mark_failure(source, reason)
        db.commit()
        summary.update(health=source.health, error=reason)
        return summary

    tokens = _terms_tokens(terms)
    for item in items:
        if source.connector_type not in _SEARCH_CONNECTORS and not _record_matches_terms(item, tokens):
            continue
        published_dt = parse_datetime(item.published_at)
        published_key = published_dt.isoformat() if published_dt else ""
        fpr = content_hash(item.title, item.publisher, published_key)
        existing_id, reason = _dedupe_target(db, fpr, item.canonical_url)
        sig = title_signature(item.title)
        syndication = _syndication_key(db, sig)
        record = OsintRecord(
            source_id=source.id,
            source_url=item.source_url,
            canonical_url=item.canonical_url,
            publisher=item.publisher,
            author=item.author,
            title=(item.title or "")[:1024],
            content=(item.content or "")[:100000] or None,
            published_at=published_dt,
            retrieved_at=datetime.now(timezone.utc),
            content_hash=fpr,
            source_type=item.source_type,
            authority_level=source.authority,
            extraction_method=item.extraction_method,
            language=(item.language or "")[:16] or None,
            jurisdiction=source.jurisdiction,
            syndication_group=syndication,
            duplicate_of=existing_id,
            duplicate_reason=reason,
            terms_matched=_record_matches_terms(item, tokens),
        )
        db.add(record)
        db.flush()
        mention_count = _extract_mentions(db, record, f"{item.title or ''} {item.content or ''}")
        summary["mentions"] += mention_count
        if record.duplicate_of is None:
            summary["new_records"] += 1
        else:
            summary["duplicates"] += 1
        summary["stored"].append({"id": str(record.id), "title": record.title,
                                 "duplicate": bool(record.duplicate_of),
                                 "reason": record.duplicate_reason})

    _mark_success(source)
    db.commit()
    summary.update(
        ok=True,
        health=source.health,
        elapsed_ms=round((time.monotonic() - started) * 1000),
    )
    return summary


def targeted_collection(
    db: Session,
    source_ids: list[uuid.UUID] | None,
    *,
    terms: str | None,
    days: int | None = None,
    max_records: int = 30,
) -> list[dict[str, Any]]:
    """Collect across enabled sources (targeted). Returns per-source summaries."""
    stmt = select(OsintSource).where(OsintSource.enabled.is_(True))
    if source_ids:
        stmt = stmt.where(OsintSource.id.in_(source_ids))
    sources = db.scalars(stmt).all()
    results: list[dict[str, Any]] = []
    for source in sources:
        results.append(
            run_source_collection(
                db, source, terms=terms, days=days, max_records=max_records
            )
        )
    return results


# ---------------------------------------------------------------------------
# Promotion into intelligence
# ---------------------------------------------------------------------------

def _intel_source(db: Session, record: OsintRecord) -> IntelligenceSource:
    name = record.publisher or record.source.name or "OSINT"
    existing = db.scalar(
        select(IntelligenceSource).where(
            IntelligenceSource.name == name,
            IntelligenceSource.source_type == "OSINT",
        )
    )
    if existing is not None:
        return existing
    row = IntelligenceSource(
        name=name[:255],
        source_type="OSINT",
        reliability_default=_AUTHORITY_RELIABILITY.get(record.authority_level or "", "C"),
        confidentiality="INTERNAL",
        activity=True,
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def promote_record(
    db: Session,
    record: OsintRecord,
    user: User,
    *,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    confidence: float | None = None,
) -> IntelligenceReport:
    """Promote an OSINT record into the intelligence domain as a report with
    full provenance back to the raw record."""
    from app.models.intelligence import SUBJECT_TYPES

    if subject_type and subject_type.upper() not in SUBJECT_TYPES:
        raise ValueError(
            f"Unsupported subject type; expected one of {', '.join(SUBJECT_TYPES)}"
        )
    if bool(subject_type) != bool(subject_id):
        raise ValueError("subject_type and subject_id must be provided together")
    st = subject_type.upper() if subject_type else None

    source = _intel_source(db, record)
    from app.services.audit_service import record_audit

    title = (record.title or "").strip()[:255] or f"OSINT record {record.id}"
    report = IntelligenceReport(
        source_id=source.id,
        subject_type=st,
        subject_id=subject_id if st else None,
        title=title,
        description=(record.content or "")[:200000] or None,
        report_date=published_date_of(record.published_at),
        ingestion_date=record.retrieved_at,
        reliability=source.reliability_default,
        information_quality=None,
        confidentiality="INTERNAL",
        status="NEW",
        info_category="OSINT",
        is_duplicate=False,
        url=(record.source_url or record.canonical_url),
        canonical_url=record.canonical_url,
        publisher=record.publisher,
        retrieved_at=record.retrieved_at,
        content_hash=record.content_hash,
        osint_record_id=record.id,
        created_by=user.id,
    )
    db.add(report)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="OSINT_PROMOTED",
        entity_type="INTELLIGENCE_REPORT",
        entity_id=str(report.id),
        metadata={
            "osint_record_id": str(record.id),
            "osint_source_id": record.source.source_id,
            "subject_type": st,
            "subject_id": str(subject_id) if subject_id else None,
            "title": report.title,
        },
    )
    db.commit()
    return report


# ---------------------------------------------------------------------------
# Claims (§53-§54)
# ---------------------------------------------------------------------------

def create_claim(
    db: Session,
    user: User,
    *,
    record_id: uuid.UUID | None = None,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    subject_label: str | None = None,
    predicate: str,
    object_value: str,
    confidence: float | None = None,
    notes: str | None = None,
) -> OsintClaim:
    claim = OsintClaim(
        record_id=record_id,
        subject_type=(subject_type or "").upper() or None,
        subject_id=subject_id,
        subject_label=subject_label,
        predicate=predicate.strip()[:64],
        object_value=object_value.strip(),
        confidence=confidence,
        verification="UNREVIEWED",
        notes=notes,
        created_by=user.id,
    )
    db.add(claim)
    db.flush()
    from app.services.audit_service import record_audit

    record_audit(
        db,
        actor_id=user.id,
        action="CLAIM_CREATED",
        entity_type="OSINT_CLAIM",
        entity_id=str(claim.id),
        metadata={"record_id": str(record_id) if record_id else None,
                  "predicate": claim.predicate, "verification": claim.verification},
    )
    db.commit()
    return claim


def review_claim(
    db: Session,
    claim: OsintClaim,
    user: User,
    *,
    verification: str,
    notes: str | None = None,
    confidence: float | None = None,
) -> OsintClaim:
    from app.models.osint import CLAIM_STATES

    verification = verification.upper()
    if verification not in CLAIM_STATES:
        raise ValueError(f"Unsupported verification state {verification!r}")
    claim.verification = verification
    if notes is not None:
        claim.notes = notes
    if confidence is not None:
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0 and 1")
        claim.confidence = confidence
    claim.reviewed_by = user.id
    claim.reviewed_at = datetime.now(timezone.utc)
    from app.services.audit_service import record_audit

    record_audit(
        db,
        actor_id=user.id,
        action="CLAIM_REVIEWED",
        entity_type="OSINT_CLAIM",
        entity_id=str(claim.id),
        metadata={"verification": verification},
    )
    db.commit()
    return claim