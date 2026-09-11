"""OSINT management + collection APIs (gate §688-§744, §1006).

Read: source registry (with health) and collected records (with provenance).
Collection: targeted, rate-limited, SSRF-guided; failures surface as source health.
Promotion: an OSINT record becomes an IntelligenceReport (provenance preserved).
Claims: analyst claim model with verification workflow (§53-§54).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.identity import User
from app.models.intelligence import IntelligenceReport
from app.models.osint import (
    AUTHORITY_TIERS,
    OsintClaim,
    OsintMention,
    OsintRecord,
    OsintSource,
)
from app.osint.common import is_public_url
from app.osint.connectors.registry import connector_types, get_connector
from app.osint.seeds import seed_default_osint_sources
from app.osint.service import (
    create_claim,
    promote_record,
    review_claim,
    run_source_collection,
    targeted_collection,
)
from app.security.rbac import Permissions

router = APIRouter(tags=["osint"])

_READ = [Depends(require_permissions(Permissions.OSINT_READ))]
_COLLECT = [Depends(require_permissions(Permissions.OSINT_COLLECT))]
_ADMIN = [Depends(require_permissions(Permissions.OSINT_ADMIN))]
_PROMOTE = [Depends(require_permissions(Permissions.INTELLIGENCE_CREATE))]


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _source_shape(s: OsintSource) -> dict:
    return {
        "id": str(s.id),
        "source_id": s.source_id,
        "name": s.name,
        "connector_type": s.connector_type,
        "url": s.url,
        "authority": s.authority,
        "jurisdiction": s.jurisdiction,
        "enabled": s.enabled,
        "poll_frequency_min": s.poll_frequency_min,
        "rate_limit_per_min": s.rate_limit_per_min,
        "health": s.health,
        "consecutive_failures": s.consecutive_failures,
        "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
        "last_failure_at": s.last_failure_at.isoformat() if s.last_failure_at else None,
        "last_failure_reason": s.last_failure_reason,
        "connector_kind": get_connector(s.connector_type).source_kind
        if get_connector(s.connector_type)
        else None,
    }


def _record_shape(r: OsintRecord) -> dict:
    return {
        "id": str(r.id),
        "source_id": str(r.source_id),
        "source": r.source.name,
        "source_type": r.source_type,
        "authority_level": r.authority_level,
        "title": r.title,
        "publisher": r.publisher,
        "author": r.author,
        "source_url": r.source_url,
        "canonical_url": r.canonical_url,
        "published_at": r.published_at.isoformat() if r.published_at else None,
        "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
        "content_hash": r.content_hash,
        "language": r.language,
        "jurisdiction": r.jurisdiction,
        "extraction_method": r.extraction_method,
        "is_duplicate": r.is_duplicate,
        "duplicate_reason": r.duplicate_reason,
        "duplicate_of": str(r.duplicate_of) if r.duplicate_of else None,
        "syndication_group": r.syndication_group,
        "terms_matched": r.terms_matched,
    }


def _mention_shape(m: OsintMention) -> dict:
    return {
        "id": str(m.id),
        "subject_type": m.subject_type,
        "subject_id": str(m.subject_id),
        "subject_label": m.subject_label,
        "match_kind": m.match_kind,
    }


def _claim_shape(c: OsintClaim) -> dict:
    return {
        "id": str(c.id),
        "record_id": str(c.record_id) if c.record_id else None,
        "subject_type": c.subject_type,
        "subject_id": str(c.subject_id) if c.subject_id else None,
        "subject_label": c.subject_label,
        "predicate": c.predicate,
        "object_value": c.object_value,
        "confidence": c.confidence,
        "verification": c.verification,
        "notes": c.notes,
        "created_by": str(c.created_by) if c.created_by else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "reviewed_by": str(c.reviewed_by) if c.reviewed_by else None,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
    }


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

@router.get("/osint/connector-types", dependencies=_READ, summary="Available OSINT connector families")
def osint_connector_types() -> dict:
    rows = []
    for ctype in connector_types():
        cls = get_connector(ctype)
        rows.append(
            {
                "connector_type": ctype,
                "source_kind": cls.source_kind if cls else None,
                "search_driven": ctype in {"gdelt"},
            }
        )
    return {"count": len(rows), "connectors": rows}


@router.get("/osint/sources", dependencies=_READ, summary="List OSINT source registry")
def list_osint_sources(
    connector_type: Annotated[str | None, Query()] = None,
    authority: Annotated[str | None, Query()] = None,
    include_disabled: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(OsintSource)
    if connector_type:
        stmt = stmt.where(OsintSource.connector_type == connector_type)
    if authority:
        stmt = stmt.where(OsintSource.authority == authority)
    if not include_disabled:
        stmt = stmt.where(OsintSource.enabled.is_(True))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(OsintSource.name).offset(offset).limit(limit)).all()
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "sources": [_source_shape(s) for s in rows],
    }


class SourceCreateBody(BaseModel):
    source_id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    connector_type: str
    url: str
    authority: str = "PUBLIC_NEWS"
    jurisdiction: str | None = None
    enabled: bool = True
    poll_frequency_min: int | None = Field(default=None, ge=5)
    rate_limit_per_min: int = Field(default=5, ge=0)
    extra_config: dict | None = None


@router.post("/osint/sources", dependencies=_ADMIN, summary="Register an OSINT source (config only)")
def create_osint_source(
    body: SourceCreateBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ctype = body.connector_type.lower()
    if get_connector(ctype) is None:
        raise HTTPException(status_code=422, detail=f"Unknown connector type {ctype!r}")
    if body.authority not in AUTHORITY_TIERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported authority; expected one of {', '.join(AUTHORITY_TIERS)}",
        )
    if not is_public_url(body.url):
        raise HTTPException(status_code=422, detail="Only public http/https source URLs are allowed")
    if db.scalar(select(OsintSource).where(OsintSource.source_id == body.source_id.strip())):
        raise HTTPException(status_code=409, detail="source_id already registered")

    row = OsintSource(
        source_id=body.source_id.strip(),
        name=body.name.strip(),
        connector_type=ctype,
        url=body.url.strip(),
        authority=body.authority,
        jurisdiction=body.jurisdiction,
        enabled=body.enabled,
        poll_frequency_min=body.poll_frequency_min,
        rate_limit_per_min=body.rate_limit_per_min,
        extra_config=body.extra_config,
    )
    db.add(row)
    db.commit()
    return _source_shape(row)


class SourceUpdateBody(BaseModel):
    name: str | None = None
    url: str | None = None
    authority: str | None = None
    jurisdiction: str | None = None
    enabled: bool | None = None
    poll_frequency_min: int | None = None
    rate_limit_per_min: int | None = None
    extra_config: dict | None = None


@router.patch("/osint/sources/{source_id}", dependencies=_ADMIN, summary="Update an OSINT source")
def update_osint_source(
    source_id: uuid.UUID,
    body: SourceUpdateBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = db.get(OsintSource, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT source not found")
    if body.url is not None and body.url != row.url:
        if not is_public_url(body.url):
            raise HTTPException(status_code=422, detail="Only public http/https source URLs are allowed")
        row.url = body.url.strip()
    if body.name is not None:
        row.name = body.name.strip()
    if body.authority is not None:
        if body.authority not in AUTHORITY_TIERS:
            raise HTTPException(status_code=422, detail=f"Unsupported authority {body.authority!r}")
        row.authority = body.authority
    if body.jurisdiction is not None:
        row.jurisdiction = body.jurisdiction
    if body.enabled is not None:
        row.enabled = body.enabled
        if body.enabled:
            from app.models.osint import HEALTH_DISABLED

            if row.health == HEALTH_DISABLED:
                row.health = "ACTIVE"
    if body.poll_frequency_min is not None:
        row.poll_frequency_min = body.poll_frequency_min
    if body.rate_limit_per_min is not None:
        row.rate_limit_per_min = max(0, body.rate_limit_per_min)
    if body.extra_config is not None:
        row.extra_config = body.extra_config
    db.commit()
    return _source_shape(row)


@router.delete("/osint/sources/{source_id}", dependencies=_ADMIN, summary="Remove an OSINT source")
def delete_osint_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = db.get(OsintSource, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT source not found")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": str(source_id)}


@router.get("/osint/sources/{source_id}/health", dependencies=_READ, summary="OSINT source health")
def osint_source_health(source_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    row = db.get(OsintSource, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT source not found")
    shape = _source_shape(row)
    return {
        "source_id": str(row.id),
        "source_ref": row.source_id,
        "health": row.health,
        "consecutive_failures": row.consecutive_failures,
        "last_success_at": shape["last_success_at"],
        "last_failure_at": shape["last_failure_at"],
        "last_failure_reason": row.last_failure_reason,
        "enabled": row.enabled,
    }


@router.post("/osint/sources/defaults", dependencies=_ADMIN, summary="Seed the default public source registry (config only)")
def osint_defaults(db: Session = Depends(get_db)) -> dict:
    seed_default_osint_sources(db)
    total = db.scalar(select(func.count(OsintSource.id))) or 0
    records = db.scalar(select(func.count(OsintRecord.id))) or 0
    return {"ok": True, "sources_total": total, "records_total": records}


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

class CollectBody(BaseModel):
    terms: str | None = Field(default=None, max_length=512)
    days: int | None = Field(default=None, ge=1, le=365)
    max_records: int = Field(default=30, ge=1, le=100)


@router.post("/osint/sources/{source_id}/collect", dependencies=_COLLECT, summary="Collect one source")
def collect_source(
    source_id: uuid.UUID,
    body: CollectBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = db.get(OsintSource, source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT source not found")
    summary = run_source_collection(
        db, row, terms=body.terms, days=body.days, max_records=body.max_records
    )
    return {
        **summary,
        "requested_by": str(user.id),
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }


class TargetedCollectBody(BaseModel):
    terms: str = Field(min_length=2, max_length=512)
    days: int | None = Field(default=None, ge=1, le=365)
    max_records: int = Field(default=30, ge=1, le=100)
    source_ids: list[uuid.UUID] | None = None


@router.post("/osint/collect", dependencies=_COLLECT, summary="Targeted collection across enabled sources")
def collect_targeted(
    body: TargetedCollectBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    results = targeted_collection(
        db,
        body.source_ids,
        terms=body.terms,
        days=body.days,
        max_records=body.max_records,
    )
    return {
        "terms": body.terms,
        "requested_by": str(user.id),
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "sources_run": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@router.get("/osint/records", dependencies=_READ, summary="List collected OSINT records")
def list_osint_records(
    source_id: Annotated[uuid.UUID | None, Query()] = None,
    q: Annotated[str | None, Query(description="Search title/publisher")] = None,
    authority: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    include_duplicates: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(OsintRecord)
    if source_id:
        stmt = stmt.where(OsintRecord.source_id == source_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                OsintRecord.title.ilike(like),
                OsintRecord.publisher.ilike(like),
            )
        )
    if authority:
        stmt = stmt.where(OsintRecord.authority_level == authority)
    if not include_duplicates:
        stmt = stmt.where(OsintRecord.duplicate_of.is_(None))
    if date_from:
        stmt = stmt.where(OsintRecord.published_at >= date_from)
    if date_to:
        stmt = stmt.where(OsintRecord.published_at <= date_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(OsintRecord.retrieved_at.desc()).offset(offset).limit(limit)).all()
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "records": [_record_shape(r) for r in rows],
    }


@router.get("/osint/records/{record_id}", dependencies=_READ, summary="OSINT record detail with provenance")
def osint_record_detail(record_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    row = db.get(OsintRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT record not found")
    mentions = db.scalars(select(OsintMention).where(OsintMention.record_id == row.id)).all()
    claims = db.scalars(select(OsintClaim).where(OsintClaim.record_id == row.id)).all()
    promoted = db.scalar(
        select(func.count(IntelligenceReport.id)).where(
            IntelligenceReport.osint_record_id == row.id
        )
    ) or 0
    return {
        **_record_shape(row),
        "source": _source_shape(row.source),
        "content": row.content,
        "mentions": [_mention_shape(m) for m in mentions],
        "claims": [_claim_shape(c) for c in claims],
        "promoted_reports": promoted,
    }


@router.get("/osint/records/{record_id}/dedupe-cluster", dependencies=_READ, summary="Syndication/dedupe cluster for a record")
def record_dedupe_cluster(record_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    row = db.get(OsintRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT record not found")
    signature = (row.syndication_group or "").split("-")[0] if row.syndication_group else None
    members = []
    if signature:
        members = db.scalars(
            select(OsintRecord).where(
                OsintRecord.syndication_group.ilike(f"{signature}%")
            )
        ).all()
    publishers = {m.publisher for m in members if m.publisher}
    return {
        "record_id": str(row.id),
        "syndication_group": row.syndication_group,
        "member_count": len(members),
        "independent_sources": len(publishers),
        "publishers": sorted(publisher for publisher in publishers if publisher),
        "members": [_record_shape(m) for m in members],
    }


class PromoteBody(BaseModel):
    subject_type: str | None = None
    subject_id: uuid.UUID | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


@router.post("/osint/records/{record_id}/promote", dependencies=_PROMOTE, summary="Promote an OSINT record to intelligence")
def promote_osint_record(
    record_id: uuid.UUID,
    body: PromoteBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = db.get(OsintRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT record not found")
    try:
        report = promote_record(
            db,
            row,
            user,
            subject_type=body.subject_type,
            subject_id=body.subject_id,
            confidence=body.confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "ok": True,
        "report_id": str(report.id),
        "osint_record_id": str(row.id),
        "title": report.title,
        "source_id": str(report.source_id),
    }


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------

class ClaimCreateBody(BaseModel):
    subject_type: str | None = None
    subject_id: uuid.UUID | None = None
    subject_label: str | None = None
    predicate: str = Field(min_length=2, max_length=64)
    object_value: str = Field(min_length=2)
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None


@router.post("/osint/records/{record_id}/claims", dependencies=_ADMIN, summary="Create an analyst claim from a record")
def create_osint_claim(
    record_id: uuid.UUID,
    body: ClaimCreateBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = db.get(OsintRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="OSINT record not found")
    try:
        claim = create_claim(
            db,
            user,
            record_id=row.id,
            subject_type=body.subject_type,
            subject_id=body.subject_id,
            subject_label=body.subject_label,
            predicate=body.predicate,
            object_value=body.object_value,
            confidence=body.confidence,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _claim_shape(claim)


class ClaimReviewBody(BaseModel):
    verification: str
    notes: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


@router.patch("/osint/claims/{claim_id}", dependencies=_ADMIN, summary="Review an OSINT claim")
def review_osint_claim(
    claim_id: uuid.UUID,
    body: ClaimReviewBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    claim = db.get(OsintClaim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="OSINT claim not found")
    try:
        review_claim(
            db,
            claim,
            user,
            verification=body.verification,
            notes=body.notes,
            confidence=body.confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _claim_shape(claim)