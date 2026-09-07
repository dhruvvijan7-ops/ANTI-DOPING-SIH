"""Investigation reports API (STAGE I).

Reports snapshot grounded case data plus investigator-controlled text. Versioning is
row-based: editing a FINAL report supersedes it and creates the next version.
Findings inside a report always come from the investigation's recorded findings,
which only the investigator can create or change.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.ai.retrieval import build_case_context
from app.ai.service import DeterministicFallbackAIService
from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.identity import User
from app.models.investigations import Investigation
from app.models.reports import InvestigationReport
from app.security.rbac import Permissions
from app.services.audit_service import record_audit

router = APIRouter(tags=["reports"])


class ReportCreateBody(BaseModel):
    title: str | None = None
    purpose: str | None = None
    outcome: str | None = None
    unresolved_questions: list[str] | None = None


class ReportPatchBody(BaseModel):
    title: str | None = None
    purpose: str | None = None
    outcome: str | None = None
    unresolved_questions: list[str] | None = None


def _inv(db: Session, investigation_id: uuid.UUID) -> Investigation:
    inv = db.get(Investigation, investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


def _report(db: Session, investigation_id: uuid.UUID, report_id: uuid.UUID) -> InvestigationReport:
    report = db.get(InvestigationReport, report_id)
    if report is None or report.investigation_id != investigation_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _serialize(report: InvestigationReport) -> dict:
    return {
        "id": str(report.id),
        "investigation_id": str(report.investigation_id),
        "version": report.version,
        "title": report.title,
        "status": report.status,
        "purpose": report.purpose,
        "outcome": report.outcome,
        "sections": report.sections_json,
        "created_by": str(report.created_by) if report.created_by else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


def _build_sections(db: Session, inv: Investigation, purpose: str | None, outcome: str | None,
                    unresolved_questions: list[str] | None, version: int) -> dict:
    ctx = build_case_context(db, inv)
    sections = DeterministicFallbackAIService().report_draft(
        ctx, purpose=purpose, outcome=outcome, unresolved_questions=unresolved_questions
    )["sections"]
    sections["audit_metadata"]["version"] = version
    return sections


def _next_version(db: Session, inv: Investigation) -> int:
    current = db.scalar(select(func.max(InvestigationReport.version)).where(
        InvestigationReport.investigation_id == inv.id
    ))
    return (current or 0) + 1


def _apply_body(report: InvestigationReport, body: ReportCreateBody | ReportPatchBody, sections: dict) -> None:
    if body.title is not None:
        report.title = body.title
    report.purpose = body.purpose if body.purpose is not None else report.purpose
    report.outcome = body.outcome if body.outcome is not None else report.outcome
    if body.unresolved_questions is not None:
        sections["unresolved_questions"] = list(body.unresolved_questions)
    report.sections_json = sections


@router.get("/investigations/{investigation_id}/reports", dependencies=[Depends(require_permissions(Permissions.REPORTS_READ))])
def list_reports(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = _inv(db, investigation_id)
    rows = list(inv.reports)
    rows.sort(key=lambda r: (r.version or 0), reverse=True)
    return {"count": len(rows), "reports": [_serialize(r) for r in rows]}


@router.post("/investigations/{investigation_id}/reports", dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def create_report(
    investigation_id: uuid.UUID,
    body: ReportCreateBody | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _inv(db, investigation_id)
    body = body or ReportCreateBody()
    version = _next_version(db, inv)
    title = body.title or f"Investigation report {inv.case_ref}"
    report = InvestigationReport(
        investigation_id=inv.id,
        version=version,
        title=title[:255],
        status="DRAFT",
        created_by=user.id,
    )
    report.sections_json = _build_sections(db, inv, body.purpose, body.outcome, body.unresolved_questions, version)
    report.purpose = body.purpose
    report.outcome = body.outcome
    db.add(report)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="REPORT_CREATED",
        entity_type="REPORT",
        entity_id=str(report.id),
        metadata={"investigation_id": str(inv.id), "version": report.version, "title": report.title},
    )
    db.commit()
    return _serialize(report)


@router.get("/investigations/{investigation_id}/reports/{report_id}", dependencies=[Depends(require_permissions(Permissions.REPORTS_READ))])
def report_detail(investigation_id: uuid.UUID, report_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    report = _report(db, investigation_id, report_id)
    body = _serialize(report)
    from app.models.audit import AuditEvent  # noqa: PLC0415
    rows = list(db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "REPORT", AuditEvent.entity_id == str(report.id))).all())
    body["audit_events"] = [
        {
            "id": str(e.id),
            "action": e.action,
            "actor": e.actor.full_name or e.actor.username if e.actor else None,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "metadata": e.metadata_json,
        }
        for e in rows
    ]
    return body


@router.patch("/investigations/{investigation_id}/reports/{report_id}", dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def update_report(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    body: ReportPatchBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    inv = _inv(db, investigation_id)
    report = _report(db, investigation_id, report_id)
    if report.status == "FINAL":
        # Versioning: supersede the published report and open the next version.
        report.status = "SUPERSEDED"
        version = _next_version(db, inv)
        fresh = InvestigationReport(
            investigation_id=inv.id,
            version=version,
            title=report.title,
            status="DRAFT",
            purpose=report.purpose,
            outcome=report.outcome,
            created_by=user.id,
        )
        fresh.sections_json = _build_sections(db, inv, report.purpose, report.outcome, None, version)
        _apply_body(fresh, body, fresh.sections_json)
        db.add(fresh)
        db.flush()
        record_audit(
            db,
            actor_id=user.id,
            action="REPORT_VERSIONED",
            entity_type="REPORT",
            entity_id=str(report.id),
            metadata={"investigation_id": str(inv.id), "superseded_version": report.version, "new_version": version},
        )
        record_audit(
            db,
            actor_id=user.id,
            action="REPORT_CREATED",
            entity_type="REPORT",
            entity_id=str(fresh.id),
            metadata={"investigation_id": str(inv.id), "version": fresh.version},
        )
        db.commit()
        return _serialize(fresh)

    _apply_body(report, body, report.sections_json)
    record_audit(
        db,
        actor_id=user.id,
        action="REPORT_UPDATED",
        entity_type="REPORT",
        entity_id=str(report.id),
        metadata={"investigation_id": str(inv.id), "version": report.version},
    )
    db.commit()
    return _serialize(report)


@router.post("/investigations/{investigation_id}/reports/{report_id}/publish", dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def publish_report(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    report = _report(db, investigation_id, report_id)
    if report.status == "FINAL":
        raise HTTPException(status_code=409, detail="Report already published")
    report.status = "FINAL"
    record_audit(
        db,
        actor_id=user.id,
        action="REPORT_PUBLISHED",
        entity_type="REPORT",
        entity_id=str(report.id),
        metadata={"investigation_id": str(investigation_id), "version": report.version},
    )
    db.commit()
    return _serialize(report)