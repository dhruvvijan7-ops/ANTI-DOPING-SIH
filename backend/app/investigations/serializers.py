"""Dict serializers for the investigation workspace (STAGE F/G)."""
from __future__ import annotations

from datetime import datetime

from app.investigations.evidence_integrity import content_hash, evidence_fields


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _user_name(user) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


def investigation_summary(row) -> dict:
    return {
        "id": str(row.id),
        "case_ref": row.case_ref,
        "title": row.title,
        "status": row.status,
        "priority": row.priority,
        "subject_type": row.subject_type,
        "subject_id": str(row.subject_id),
        "originating_alert_id": str(row.originating_alert_id) if row.originating_alert_id else None,
        "assigned_to": str(row.assigned_to) if row.assigned_to else None,
        "assigned_to_name": _user_name(getattr(row, "assignee", None)),
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def evidence_item(row) -> dict:
    current = evidence_fields(row)
    sha256 = getattr(row, "sha256_hash", None)
    computed = content_hash(current) if sha256 else None
    return {
        "id": str(row.id),
        "investigation_id": str(row.investigation_id),
        "title": row.title,
        "description": row.description,
        "evidence_type": row.evidence_type,
        "source": row.source,
        "classification": row.classification,
        "sensitivity": row.sensitivity,
        "version": row.version,
        "item_date": _iso(row.item_date),
        "relationship_to_case": row.relationship_to_case,
        "integrity": {
            "algorithm": "sha256",
            "canonical_form": "clean-sport-evidence-v1",
            "value": sha256,
            "verified": bool(sha256) and computed == sha256,
        },
        "deleted": getattr(row, "deleted_at", None) is not None,
        "deleted_at": _iso(getattr(row, "deleted_at", None)),
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def evidence_version_row(row) -> dict:
    return {
        "version": row.version_number,
        "title": row.title,
        "description": row.description,
        "evidence_type": row.evidence_type,
        "source": row.source,
        "classification": row.classification,
        "sensitivity": row.sensitivity,
        "sha256": row.sha256_hash,
        "item_date": _iso(row.item_date),
        "relationship_to_case": row.relationship_to_case,
        "changed_by": str(row.changed_by) if row.changed_by else None,
        "changed_by_name": _user_name(getattr(row, "changer", None)),
        "change_reason": row.change_reason,
        "created_at": _iso(row.created_at),
    }


def evidence_link_row(row) -> dict:
    return {
        "link_id": str(row.id),
        "evidence_id": str(row.evidence_id),
        "validity": row.validity,
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": _iso(row.created_at),
    }


def task_row(row) -> dict:
    return {
        "id": str(row.id),
        "investigation_id": str(row.investigation_id),
        "title": row.title,
        "description": row.description,
        "assigned_to": str(row.assigned_to) if row.assigned_to else None,
        "assigned_to_name": _user_name(getattr(row, "assignee", None)),
        "status": row.status,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "created_by": str(row.created_by) if row.created_by else None,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def note_row(row) -> dict:
    return {
        "id": str(row.id),
        "investigation_id": str(row.investigation_id),
        "author_id": str(row.author_id) if row.author_id else None,
        "author": _user_name(getattr(row, "author", None)),
        "content": row.content,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def finding_row(row) -> dict:
    return {
        "id": str(row.id),
        "investigation_id": str(row.investigation_id),
        "title": row.title,
        "statement": row.statement,
        "supporting_evidence": row.supporting_evidence,
        "assessment": row.assessment,
        "confident": row.confident,
        "author_id": str(row.author_id) if row.author_id else None,
        "author": _user_name(getattr(row, "author", None)),
        "evidence_links": [evidence_link_row(link) for link in row.evidence_links],
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }