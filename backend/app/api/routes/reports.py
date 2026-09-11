"""Investigation reports API (STAGE I + Reporting gate).

Reports are a genuine in-app writing workspace: investigators edit a structured
rich-text document inside VERITY (no external office app), can generate grounded
AI drafts, get per-section AI assistance, autosave a draft, review versions and
publish. Exports (print HTML, DOCX, PDF) embed full provenance.

Key invariants:
* A report is always linked to an investigation/case (§559).
* The editor never opens an external window (§560).
* Inserted/grounded blocks carry references to real case records (§563, §571).
* Autosave never destroys user text (§564); it writes to draft columns only.
* AI output is labelled (human/ai/ai_edited) at the data level (§567, §353).
* Only an authorized human can publish/finalize; AI cannot auto-promote DRAFT
  to FINAL (§355, §569).
* Every mutation produces an audit event (§138).
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.ai.retrieval import build_case_context
from app.ai.service import get_ai_service
from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.identity import User
from app.models.investigations import Investigation
from app.models.reports import (
    InvestigationReport,
    REPORT_STATUSES,
    REPORT_TYPES,
)
from app.reports.render import (
    ReportRenderContext,
    build_standalone_html,
    document_to_docx_bytes,
    document_to_pdf_bytes,
)
from app.reports.schemas import DocumentBlocksBody, ReportTypeBody, normalize_blocks
from app.security.rbac import Permissions
from app.services.audit_service import record_audit

router = APIRouter(tags=["reports"])

# Statuses that are considered "locked" snapshots (no further writer edits).
_LOCKED = ("FINAL", "SUPERSEDED", "ARCHIVED")

ASTS = {  # AI assistance "section slugs" we support -> canonical label
    "timeline": "Timeline summary",
    "evidence": "Evidence summary",
    "findings": "Findings",
    "intelligence": "Intelligence assessment",
    "relationships": "Relationship summary",
    "gaps": "Gaps",
    "questions": "Investigative questions",
    "assessment": "Assessment",
}


class ReportCreateBody(BaseModel):
    title: str | None = None
    purpose: str | None = None
    outcome: str | None = None
    unresolved_questions: list[str] | None = None
    report_type: str | None = None


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


def _author_name(user: User | None) -> str:
    if user is None:
        return "Unknown"
    return user.full_name or user.username


def _serialize(report: InvestigationReport) -> dict:
    return {
        "id": str(report.id),
        "investigation_id": str(report.investigation_id),
        "version": report.version,
        "title": report.title,
        "report_type": report.report_type,
        "status": report.status,
        "purpose": report.purpose,
        "outcome": report.outcome,
        "sections": report.sections_json,
        "blocks": report.document_blocks,
        "draft": report.draft_blocks,
        "draft_saved_at": report.draft_saved_at.isoformat() if report.draft_saved_at else None,
        "published_at": report.published_at.isoformat() if report.published_at else None,
        "created_by": str(report.created_by) if report.created_by else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


def _build_sections(db: Session, inv: Investigation, purpose: str | None, outcome: str | None,
                    unresolved_questions: list[str] | None, version: int) -> dict:
    from app.ai.service import DeterministicFallbackAIService  # noqa: PLC0415
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


def _provenance_ctx(db: Session, report: InvestigationReport, user: User | None) -> ReportRenderContext:
    inv = db.get(Investigation, report.investigation_id)
    return ReportRenderContext(
        case_ref=inv.case_ref if inv else "",
        report_version=report.version,
        author=_author_name(user),
        status=report.status,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _apply_body(report: InvestigationReport, body: ReportCreateBody | ReportPatchBody, sections: dict) -> None:
    if body.title is not None:
        report.title = body.title
    report.purpose = body.purpose if body.purpose is not None else report.purpose
    report.outcome = body.outcome if body.outcome is not None else report.outcome
    if getattr(body, "unresolved_questions", None) is not None:
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
    title = (body.title or "").strip() or f"Investigation report {inv.case_ref}"
    report = InvestigationReport(
        investigation_id=inv.id,
        version=version,
        title=title[:255],
        status="DRAFT",
        report_type=(body.report_type or "MANUAL").upper() if (body.report_type or "MANUAL").upper() in REPORT_TYPES else "MANUAL",
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
        metadata={"investigation_id": str(inv.id), "version": report.version, "title": report.title,
                  "report_type": report.report_type},
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
    if report.status == "ARCHIVED":
        raise HTTPException(status_code=409, detail="Cannot edit an archived report.")
    if report.status in ("FINAL", "SUPERSEDED"):
        # Editing a published/superseded report opens the next draft version and
        # supersedes the prior row; the finalized version stays recoverable (§566).
        if report.status == "FINAL":
            report.status = "SUPERSEDED"
        version = _next_version(db, inv)
        fresh = InvestigationReport(
            investigation_id=inv.id,
            version=version,
            title=report.title,
            status="DRAFT",
            report_type=report.report_type,
            purpose=report.purpose,
            outcome=report.outcome,
            created_by=user.id,
        )
        fresh.sections_json = _build_sections(db, inv, report.purpose, report.outcome, None, version)
        fresh.document_blocks = list(report.document_blocks)
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
    report.published_at = None
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


@router.post("/investigations/{investigation_id}/reports/{report_id}/document",
             dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def save_report_document(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    body: DocumentBlocksBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Persist (or autosave) the structured editor document."""
    inv = _inv(db, investigation_id)
    report = _report(db, investigation_id, report_id)
    if report.status in _LOCKED:
        raise HTTPException(status_code=409, detail=f"Cannot edit a {report.status} report.")
    blocks = normalize_blocks([b.to_storage() for b in body.blocks])
    if body.title:
        report.title = body.title[:255]
    if body.autosave:
        # Autosave writes to draft columns only; the persisted version stays intact.
        report.draft_blocks = blocks
        report.draft_saved_at = datetime.now(timezone.utc)
        action = "REPORT_AUTOSAVED"
    else:
        report.document_blocks = blocks
        report.draft_blocks = blocks
        report.draft_saved_at = datetime.now(timezone.utc)
        action = "REPORT_DOCUMENT_SAVED"
    record_audit(
        db,
        actor_id=user.id,
        action=action,
        entity_type="REPORT",
        entity_id=str(report.id),
        metadata={"investigation_id": str(inv.id), "version": report.version,
                  "blocks": len(blocks), "autosave": body.autosave},
    )
    db.commit()
    return _serialize(report)


@router.post("/investigations/{investigation_id}/reports/{report_id}/ai-draft",
             dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def create_report_ai_draft(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Regenerate the editor document as an AI-generated structured draft, fully
    grounded in the case record. Never invents data; missing categories marked."""
    inv = _inv(db, investigation_id)
    report = _report(db, investigation_id, report_id)
    if report.status in _LOCKED:
        raise HTTPException(status_code=409, detail=f"Cannot edit a {report.status} report.")
    service = get_ai_service()
    ctx = build_case_context(db, inv)
    blocks = service.report_document_draft(ctx, purpose=report.purpose)
    report.document_blocks = blocks
    report.draft_blocks = blocks
    report.draft_saved_at = datetime.now(timezone.utc)
    report.report_type = "AI_ASSISTED" if report.report_type != "HYBRID" else report.report_type
    record_audit(
        db,
        actor_id=user.id,
        action="REPORT_AI_DRAFT",
        entity_type="REPORT",
        entity_id=str(report.id),
        metadata={"investigation_id": str(inv.id), "version": report.version,
                  "blocks": len(blocks), "provider": service.provider_name},
    )
    db.commit()
    body = _serialize(report)
    body["provider"] = service.provider_name
    return body


@router.post("/investigations/{investigation_id}/reports/{report_id}/ai-section",
             dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def create_report_ai_section(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    body: dict | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Generate an AI-assisted block set for a named report section (grounded)."""
    inv = _inv(db, investigation_id)
    report = _report(db, investigation_id, report_id)
    body = body or {}
    section = (body.get("section") or "").strip()
    slug = section.lower()
    if slug not in ASTS:
        raise HTTPException(status_code=422, detail=f"Unsupported section. Choose: {', '.join(ASTS)}")
    service = get_ai_service()
    ctx = build_case_context(db, inv)
    blocks = service.report_section_assist(ctx, section)
    record_audit(
        db,
        actor_id=user.id,
        action="REPORT_AI_SECTION",
        entity_type="REPORT",
        entity_id=str(report.id),
        metadata={"investigation_id": str(inv.id), "version": report.version,
                  "section": slug, "blocks": len(blocks)},
    )
    db.commit()
    return {"section": slug, "label": ASTS[slug], "provider": service.provider_name, "blocks": blocks}


@router.post("/investigations/{investigation_id}/reports/{report_id}/type",
             dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def set_report_type(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    body: ReportTypeBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    report = _report(db, investigation_id, report_id)
    if report.status in _LOCKED:
        raise HTTPException(status_code=409, detail=f"Cannot change type of a {report.status} report.")
    report.report_type = body.report_type
    record_audit(db, actor_id=user.id, action="REPORT_TYPE_SET", entity_type="REPORT",
                 entity_id=str(report.id), metadata={"investigation_id": str(investigation_id),
                                                     "report_type": body.report_type})
    db.commit()
    return _serialize(report)


@router.post("/investigations/{investigation_id}/reports/{report_id}/review",
             dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def move_to_review(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    report = _report(db, investigation_id, report_id)
    if report.status == "FINAL":
        raise HTTPException(status_code=409, detail="Report already final.")
    if report.status == "SUPERSEDED":
        raise HTTPException(status_code=409, detail="A superseded report cannot move to review.")
    report.status = "IN_REVIEW"
    record_audit(db, actor_id=user.id, action="REPORT_TO_REVIEW", entity_type="REPORT",
                 entity_id=str(report.id), metadata={"investigation_id": str(investigation_id),
                                                     "version": report.version})
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
    if report.status == "SUPERSEDED":
        raise HTTPException(status_code=409, detail="A superseded report cannot be published directly.")
    report.status = "FINAL"
    report.published_at = datetime.now(timezone.utc)
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


@router.post("/investigations/{investigation_id}/reports/{report_id}/archive",
             dependencies=[Depends(require_permissions(Permissions.REPORTS_GENERATE))])
def archive_report(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    report = _report(db, investigation_id, report_id)
    if report.status in ("SUPERSEDED", "ARCHIVED"):
        raise HTTPException(status_code=409, detail=f"Report is already {report.status}.")
    report.status = "ARCHIVED"
    record_audit(db, actor_id=user.id, action="REPORT_ARCHIVED", entity_type="REPORT",
                 entity_id=str(report.id), metadata={"investigation_id": str(investigation_id),
                                                     "version": report.version})
    db.commit()
    return _serialize(report)


def _export_filename(report: InvestigationReport, ext: str) -> str:
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in report.title).strip("_") or "report"
    return f"{safe}_v{report.version}.{ext}"


@router.get("/investigations/{investigation_id}/reports/{report_id}/export/html",
            dependencies=[Depends(require_permissions(Permissions.REPORTS_READ))])
def export_html(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    report = _report(db, investigation_id, report_id)
    ctx = _provenance_ctx(db, report, user)
    rendered = build_standalone_html(report.title, report.document_blocks, ctx)
    return StreamingResponse(iter([rendered.encode("utf-8")]),
                             media_type="text/html",
                             headers={"Content-Disposition": f'attachment; filename="{_export_filename(report, "html")}"'})


@router.get("/investigations/{investigation_id}/reports/{report_id}/export/docx",
            dependencies=[Depends(require_permissions(Permissions.REPORTS_READ))])
def export_docx(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    report = _report(db, investigation_id, report_id)
    ctx = _provenance_ctx(db, report, user)
    data = document_to_docx_bytes(report.title, report.document_blocks, ctx)
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{_export_filename(report, "docx")}"'})


@router.get("/investigations/{investigation_id}/reports/{report_id}/export/pdf",
            dependencies=[Depends(require_permissions(Permissions.REPORTS_READ))])
def export_pdf(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    report = _report(db, investigation_id, report_id)
    ctx = _provenance_ctx(db, report, user)
    data = document_to_pdf_bytes(report.title, report.document_blocks, ctx)
    return StreamingResponse(io.BytesIO(data),
                             media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{_export_filename(report, "pdf")}"'})