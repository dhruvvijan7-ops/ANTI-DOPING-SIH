"""AI decision-support API (STAGE H).

Each operation is grounded on the records of ONE investigation and returned as
classified statements. Output is advisory only; it never decides guilt.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai import get_ai_service
from app.ai.retrieval import build_case_context
from app.ai.service import DISCLAIMER
from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.investigations import Investigation
from app.security.rbac import Permissions

router = APIRouter(tags=["ai"])

_READ = Depends(require_permissions(Permissions.INVESTIGATIONS_READ))


class SignalExplainBody(BaseModel):
    signal_type: str | None = None


class ReportDraftBody(BaseModel):
    purpose: str | None = None
    outcome: str | None = None
    unresolved_questions: list[str] | None = None


def _inv(db: Session, investigation_id: uuid.UUID) -> Investigation:
    inv = db.get(Investigation, investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


def _dispatch(operation: str, ctx, body=None):
    service = get_ai_service()
    if operation == "case_summary":
        content = service.case_summary(ctx)
    elif operation == "timeline_summary":
        content = service.timeline_summary(ctx)
    elif operation == "signal_explanation":
        content = service.signal_explanation(ctx, body.signal_type if body else None)
    elif operation == "information_gaps":
        content = service.information_gaps(ctx)
    elif operation == "investigation_questions":
        content = service.investigation_questions(ctx)
    elif operation == "report_draft":
        draft = service.report_draft(
            ctx,
            purpose=body.purpose if body else None,
            outcome=body.outcome if body else None,
            unresolved_questions=body.unresolved_questions if body else None,
        )
        return {"provider": service.provider_name, "operation": operation, "grounded": True,
                "disclaimer": DISCLAIMER, "draft": draft}
    else:  # pragma: no cover - guarded below
        raise HTTPException(status_code=404, detail="Unknown AI operation")
    return service.respond(operation, content)


@router.post("/investigations/{investigation_id}/ai/summary", dependencies=[_READ])
def ai_case_summary(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return _dispatch("case_summary", build_case_context(db, _inv(db, investigation_id)))


@router.post("/investigations/{investigation_id}/ai/timeline-summary", dependencies=[_READ])
def ai_timeline_summary(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return _dispatch("timeline_summary", build_case_context(db, _inv(db, investigation_id)))


@router.post("/investigations/{investigation_id}/ai/signal-explanation", dependencies=[_READ])
def ai_signal_explanation(
    investigation_id: uuid.UUID,
    body: SignalExplainBody | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return _dispatch("signal_explanation", build_case_context(db, _inv(db, investigation_id)), body)


@router.post("/investigations/{investigation_id}/ai/information-gaps", dependencies=[_READ])
def ai_information_gaps(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return _dispatch("information_gaps", build_case_context(db, _inv(db, investigation_id)))


@router.post("/investigations/{investigation_id}/ai/questions", dependencies=[_READ])
def ai_investigation_questions(investigation_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return _dispatch("investigation_questions", build_case_context(db, _inv(db, investigation_id)))


@router.post("/investigations/{investigation_id}/ai/report-draft", dependencies=[_READ])
def ai_report_draft(
    investigation_id: uuid.UUID,
    body: ReportDraftBody | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return _dispatch("report_draft", build_case_context(db, _inv(db, investigation_id)), body)