"""Audit event persistence.

Records security-sensitive actions (logged in/out, role changes, etc.). Audit rows
are append-only and never hard-deleted in normal workflows. See directive §37.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def record_audit(
    db: Session,
    *,
    actor_id: Optional[uuid.UUID],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> AuditEvent:
    """Persist an audit event."""
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata) if metadata else None,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    return event
