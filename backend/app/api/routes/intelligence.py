"""Intelligence read APIs (G3) + manual report creation.

Report listing/detail with source redaction: confidential source identity is not
exposed unnecessarily. For sources whose confidentiality indicates a sensitive
classification, the source name is withheld from API responses (source
type/quality metadata remains available for context).

Manual intelligence creation (gate §783/§787/§1002) is analyst work product: the
analyst selects an existing source, links the report to a subject and records the
assessment fields. It is only ever a human decision; the engine never fabricates
reports.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.identity import User
from app.models.intelligence import (
    SUBJECT_TYPES,
    IntelligenceReport,
    IntelligenceSource,
    SourceAssessment,
)
from app.security.rbac import Permissions
from app.services.audit_service import record_audit
from app.services.domain_reads import name_for, resolve_names

router = APIRouter(tags=["intelligence"])

_READ = [Depends(require_permissions(Permissions.INTELLIGENCE_READ))]
_CREATE = [Depends(require_permissions(Permissions.INTELLIGENCE_CREATE))]

# Confidentiality levels at which the source name is withheld from responses.
_REDACTED_CONFIDENTIALITY = {"CONFIDENTIAL", "RESTRICTED", "SECRET", "TOP_SECRET", "CLASSIFIED"}
_STATUSES = ("NEW", "REVIEWED", "ASSESSED")


def _source_summary(src: IntelligenceSource | None) -> dict | None:
    if src is None:
        return None
    redact = (src.confidentiality or "").upper() in _REDACTED_CONFIDENTIALITY
    return {
        "source_id": str(src.id),
        "source_type": src.source_type,
        "reliability_default": src.reliability_default,
        "confidentiality": src.confidentiality,
        "name": None if redact else src.name,
        "is_active": src.is_active,
    }


def intel_summary(r: IntelligenceReport, subject_name: str | None = None) -> dict:
    return {
        "id": str(r.id),
        "external_ref": r.external_ref,
        "title": r.title,
        "description": r.description,
        "report_date": r.report_date.isoformat() if r.report_date else None,
        "ingestion_date": r.ingestion_date.isoformat() if r.ingestion_date else None,
        "status": r.status,
        "info_category": r.info_category,
        "reliability": r.reliability,
        "information_quality": r.information_quality,
        "confidentiality": r.confidentiality,
        "is_duplicate": r.is_duplicate,
        "subject_type": r.subject_type,
        "subject_id": str(r.subject_id) if r.subject_id else None,
        "subject_name": subject_name,
        "source": _source_summary(r.source),
        "tags": [t.name for t in r.tags],
        "url": r.url,
        "canonical_url": r.canonical_url,
        "publisher": r.publisher,
        "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
        "content_hash": r.content_hash,
        "osint_record_id": str(r.osint_record_id) if r.osint_record_id else None,
    }


@router.get("/intelligence/reports", dependencies=_READ, summary="List/search intelligence reports")
def list_intelligence(
    subject_id: Annotated[uuid.UUID | None, Query()] = None,
    subject_type: Annotated[str | None, Query()] = None,
    info_category: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    source_type: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query(description="Search title/description")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    stmt = select(IntelligenceReport).join(IntelligenceSource)
    if subject_id:
        stmt = stmt.where(IntelligenceReport.subject_id == subject_id)
    if subject_type:
        stmt = stmt.where(IntelligenceReport.subject_type == subject_type.upper())
    if info_category:
        stmt = stmt.where(IntelligenceReport.info_category == info_category.upper())
    if status_filter:
        stmt = stmt.where(IntelligenceReport.status == status_filter.upper())
    if source_type:
        stmt = stmt.where(IntelligenceSource.source_type == source_type.upper())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                IntelligenceReport.title.ilike(like),
                IntelligenceReport.description.ilike(like),
            )
        )
    if date_from:
        stmt = stmt.where(IntelligenceReport.report_date >= date_from)
    if date_to:
        stmt = stmt.where(IntelligenceReport.report_date <= date_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(IntelligenceReport.ingestion_date.desc()).offset(offset).limit(limit)
    ).all()
    pairs = [
        (r.subject_type, r.subject_id)
        for r in rows
        if r.subject_id and r.subject_type
    ]
    names = resolve_names(db, pairs)
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "reports": [
            intel_summary(r, names.get((r.subject_type or "", str(r.subject_id))))
            for r in rows
        ],
    }


@router.get("/intelligence/reports/{report_id}", dependencies=_READ, summary="Intelligence report detail")
def intelligence_detail(report_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    report = db.get(IntelligenceReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Intelligence report not found")
    subject_name = (
        name_for(db, report.subject_type, report.subject_id)
        if report.subject_id and report.subject_type
        else None
    )
    assessments = db.scalars(
        select(SourceAssessment).where(SourceAssessment.report_id == report.id)
    ).all()
    return {
        **intel_summary(report, subject_name),
        "assessments": [
            {
                "id": str(a.id),
                "reliability": a.reliability,
                "information_quality": a.information_quality,
                "assessment_notes": a.assessment_notes,
                "assessed_at": a.assessed_at.isoformat() if a.assessed_at else None,
            }
            for a in assessments
        ],
    }


@router.get("/intelligence/sources", dependencies=_READ, summary="List intelligence sources")
def list_intelligence_sources(
    source_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    """Active sources available for manual intelligence recording. Source names are
    redacted for confidential classifications (same rule as report responses)."""
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    stmt = select(IntelligenceSource).where(IntelligenceSource.is_active.is_(True))
    if source_type:
        stmt = stmt.where(IntelligenceSource.source_type == source_type.upper())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(IntelligenceSource.name).offset(offset).limit(limit)).all()
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "sources": [
            {
                **(_source_summary(s) or {}),
                "external_ref": s.external_ref,
            }
            for s in rows
        ],
    }


class IntelligenceReportBody(BaseModel):
    """Manual intelligence record. The source id must reference an existing
    source; the subject link is optional but must pair type+id when provided."""

    source_id: uuid.UUID
    title: str
    description: str | None = None
    subject_type: str | None = None
    subject_id: uuid.UUID | None = None
    report_date: date | None = None
    reliability: str | None = None
    information_quality: str | None = None
    confidentiality: str = "INTERNAL"
    status: str = "NEW"
    info_category: str | None = None


@router.post("/intelligence/reports", dependencies=_CREATE, summary="Record intelligence manually")
def create_intelligence_report(
    body: IntelligenceReportBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Human-recorded intelligence: the analyst (not the engine) decides what is
    recorded, from which source, and how it should be assessed."""
    source = db.get(IntelligenceSource, body.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Intelligence source not found")

    title = (body.title or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Intelligence report requires a title")
    if bool(body.subject_type) != bool(body.subject_id):
        raise HTTPException(
            status_code=422,
            detail="subject_type and subject_id must be provided together",
        )
    subject_type = (body.subject_type or "").upper() or None
    if subject_type and subject_type not in SUBJECT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported subject type; expected one of {', '.join(SUBJECT_TYPES)}",
        )

    status = (body.status or "NEW").upper()
    if status not in _STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported status; expected one of {', '.join(_STATUSES)}",
        )

    report = IntelligenceReport(
        source_id=source.id,
        subject_type=subject_type,
        subject_id=body.subject_id if subject_type else None,
        title=title[:255],
        description=body.description,
        report_date=body.report_date,
        reliability=(body.reliability or "").upper()[:8] or None,
        information_quality=(body.information_quality or "").upper()[:8] or None,
        confidentiality=(body.confidentiality or "INTERNAL").upper()[:32],
        status=status,
        info_category=(body.info_category or "").upper()[:64] or None,
        is_duplicate=False,
        created_by=user.id,
    )
    db.add(report)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="INTELLIGENCE_CREATED",
        entity_type="INTELLIGENCE_REPORT",
        entity_id=str(report.id),
        metadata={
            "source_id": str(source.id),
            "subject_type": subject_type,
            "subject_id": str(report.subject_id) if report.subject_id else None,
            "title": report.title,
            "info_category": report.info_category,
            "status": report.status,
        },
    )
    db.commit()
    subject_name = (
        name_for(db, report.subject_type, report.subject_id)
        if report.subject_id and report.subject_type
        else None
    )
    return intel_summary(report, subject_name)