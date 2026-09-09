"""Relationship graph read APIs (G3): top-level access to the persisted
relational relationship graph with resolved entity names on both sides.

These read-only endpoints expose investigative context. A relationship between
entities NEVER implies wrongdoing -- it is contextual association for review.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_any_permission
from app.db.session import get_db
from app.models.relationships import EntityRelationship, RelationshipType
from app.security.rbac import Permissions
from app.services.domain_reads import resolve_names

router = APIRouter(tags=["relationships"])

_READ = [Depends(require_any_permission([
    Permissions.INTELLIGENCE_READ,
    Permissions.INVESTIGATIONS_READ,
    Permissions.ATHLETES_READ,
]))]


def _relationship_summary(r: EntityRelationship, names: dict[tuple[str, str], str]) -> dict:
    return {
        "id": str(r.id),
        "relationship_type": r.rel_type.name if r.rel_type else None,
        "from_entity_type": r.from_entity_type,
        "from_entity_id": str(r.from_entity_id),
        "from_name": names.get((r.from_entity_type, str(r.from_entity_id))),
        "to_entity_type": r.to_entity_type,
        "to_entity_id": str(r.to_entity_id),
        "to_name": names.get((r.to_entity_type, str(r.to_entity_id))),
        "start_date": r.start_date.isoformat() if r.start_date else None,
        "end_date": r.end_date.isoformat() if r.end_date else None,
        "confidence": r.confidence,
        "metadata": r.metadata_json,
        "status": "INACTIVE" if r.end_date else "ACTIVE",
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _resolve_for_rows(db: Session, rows: list[EntityRelationship]) -> dict[tuple[str, str], str]:
    pairs: list[tuple[str, uuid.UUID]] = []
    for r in rows:
        pairs.append((r.from_entity_type, r.from_entity_id))
        pairs.append((r.to_entity_type, r.to_entity_id))
    return resolve_names(db, pairs)


@router.get("/relationships", dependencies=_READ, summary="List entity relationships")
def list_relationships(
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    relationship_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    stmt = select(EntityRelationship).join(RelationshipType)
    if entity_type and entity_id:
        stmt = stmt.where(
            (EntityRelationship.from_entity_type == entity_type.upper())
            & (EntityRelationship.from_entity_id == entity_id)
            | (EntityRelationship.to_entity_type == entity_type.upper())
            & (EntityRelationship.to_entity_id == entity_id)
        )
    if relationship_type:
        stmt = stmt.where(RelationshipType.name == relationship_type.upper())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(EntityRelationship.created_at.desc()).offset(offset).limit(limit)
    ).all()
    names = _resolve_for_rows(db, rows)
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "relationships": [_relationship_summary(r, names) for r in rows],
    }


@router.get("/relationships/{relationship_id}", dependencies=_READ, summary="Relationship detail")
def relationship_detail(relationship_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    row = db.get(EntityRelationship, relationship_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    names = _resolve_for_rows(db, [row])
    return _relationship_summary(row, names)