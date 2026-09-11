"""Relationship graph CRUD APIs (G3 + workspace + graph gate).

Read: top-level access to the persisted relational relationship graph with
resolved entity names on both sides.  Create/Edit/Delete: manual relationship
recording (gate §786/§810) by intelligence analysts and investigators — a
descriptive association between entities, never an assertion of wrongdoing.

Graph gate (§100-112): node creation, role assignment, relationship edit,
soft-delete, enriched detail with provenance, position persistence, and
graph filters.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_any_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.intelligence import IntelligenceReport, IntelligenceSource
from app.models.investigations import Investigation, TimelineEvent
from app.models.relationships import (
    SUBJECT_TYPES,
    EntityRelationship,
    RelationshipNodeFeature,
    RelationshipType,
)
from app.models.subjects import (
    Athlete,
    Competition,
    Event,
    Location,
    Organization,
    Provider,
    Source,
    Supplement,
    SupportPerson,
    Team,
)
from app.security.rbac import Permissions
from app.services.audit_service import record_audit
from app.services.domain_reads import resolve_names

router = APIRouter(tags=["relationships"])

_READ = [Depends(require_any_permission([
    Permissions.INTELLIGENCE_READ,
    Permissions.INVESTIGATIONS_READ,
    Permissions.ATHLETES_READ,
]))]

_CREATE = [Depends(require_any_permission([
    Permissions.INTELLIGENCE_CREATE,
    Permissions.INVESTIGATIONS_MODIFY,
]))]

_MODIFY = [Depends(require_any_permission([
    Permissions.INVESTIGATIONS_MODIFY,
    Permissions.INTELLIGENCE_CREATE,
]))]

_ENTITY_MODELS = {
    "ATHLETE": Athlete,
    "TEAM": Team,
    "ORGANIZATION": Organization,
    "PROVIDER": Provider,
    "SUPPORT_PERSON": SupportPerson,
    "SUPPLEMENT": Supplement,
    "EVENT": Event,
    "COMPETITION": Competition,
    "LOCATION": Location,
    "SOURCE": Source,
}

_CANONICAL_ROLES = [
    "ATHLETE", "COACH", "TRAINER", "MEDICAL_PROFESSIONAL", "MANAGER",
    "AGENT", "SUPPLIER", "FEDERATION_OFFICIAL", "TEAM", "PROVIDER",
    "EVENT", "SOURCE", "LOCATION", "ORGANIZATION",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_relationship_type(db: Session, name: str) -> RelationshipType:
    norm = name.upper()[:64]
    existing = db.scalar(select(RelationshipType).where(RelationshipType.name == norm))
    if existing is not None:
        return existing
    row = RelationshipType(name=norm)
    db.add(row)
    db.flush()
    return row


def _relationship_summary(r: EntityRelationship, names: dict[tuple[str, str], str]) -> dict:
    """Base relationship summary — §103 detail fields where available."""
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
        "frequency": r.frequency,
        "verification": r.verification or "UNVERIFIED",
        "notes": r.notes,
        "metadata": r.metadata_json,
        "source_id": str(r.source_id) if r.source_id else None,
        "status": "INACTIVE" if r.deleted_at or r.end_date else "ACTIVE",
        "deleted": r.deleted_at is not None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _resolve_for_rows(db: Session, rows: list[EntityRelationship]) -> dict[tuple[str, str], str]:
    pairs: list[tuple[str, uuid.UUID]] = []
    for r in rows:
        pairs.append((r.from_entity_type, r.from_entity_id))
        pairs.append((r.to_entity_type, r.to_entity_id))
    return resolve_names(db, pairs)


def _entity_exists(db: Session, entity_type: str, entity_id: uuid.UUID) -> bool:
    model = _ENTITY_MODELS.get(entity_type)
    if model is None:
        return False
    return db.get(model, entity_id) is not None


def _enrich_detail(db: Session, row: EntityRelationship, names: dict[tuple[str, str], str]) -> dict:
    """§103 enriched detail: provenance, counts, related investigations."""
    base = _relationship_summary(row, names)

    # Source provenance
    source_info = None
    if row.source_id:
        src = db.get(IntelligenceSource, row.source_id)
        if src:
            source_info = {
                "id": str(src.id),
                "name": src.name,
                "source_type": src.source_type,
                "reliability_default": src.reliability_default,
                "confidentiality": src.confidentiality,
            }

    # Related intel: reports involving either entity
    intel_count = 0
    intel_titles: list[str] = []
    for entity_type, entity_id in ((row.from_entity_type, row.from_entity_id),
                                    (row.to_entity_type, row.to_entity_id)):
        cnt = db.scalar(
            select(func.count()).select_from(IntelligenceReport).where(
                IntelligenceReport.subject_type == entity_type,
                IntelligenceReport.subject_id == entity_id,
            )
        ) or 0
        intel_count += cnt
        if cnt > 0:
            reports = db.scalars(
                select(IntelligenceReport.title).where(
                    IntelligenceReport.subject_type == entity_type,
                    IntelligenceReport.subject_id == entity_id,
                ).limit(10)
            ).all()
            intel_titles.extend(reports)

    # Related investigations
    inv_rows: list[Investigation] = []
    for entity_type, entity_id in ((row.from_entity_type, row.from_entity_id),
                                    (row.to_entity_type, row.to_entity_id)):
        inv_rows.extend(
            db.scalars(
                select(Investigation).where(
                    Investigation.subject_type == entity_type,
                    Investigation.subject_id == entity_id,
                ).limit(10)
            ).all()
        )

    # Timeline events on related investigations
    timeline_count = 0
    inv_ids = {inv.id for inv in inv_rows}
    if inv_ids:
        timeline_count = db.scalar(
            select(func.count()).select_from(TimelineEvent).where(
                TimelineEvent.investigation_id.in_(inv_ids),
            )
        ) or 0

    # Deduplicate
    seen_inv: set[uuid.UUID] = set()
    related_investigations: list[dict] = []
    for inv in inv_rows:
        if inv.id not in seen_inv:
            seen_inv.add(inv.id)
            related_investigations.append({
                "id": str(inv.id),
                "case_ref": inv.case_ref,
                "title": inv.title,
                "status": inv.status,
            })

    # Audit provenance — who created this relationship
    from app.models.audit import AuditEvent
    creation_event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_type == "RELATIONSHIP",
            AuditEvent.entity_id == str(row.id),
            AuditEvent.action == "RELATIONSHIP_CREATED",
        ).order_by(AuditEvent.timestamp.asc())
    )
    provenance = {
        "source": source_info,
        "created_by_actor": str(creation_event.actor_id) if creation_event else None,
        "created_at": creation_event.timestamp.isoformat() if creation_event else None,
    }

    base["provenance"] = provenance
    base["related_intelligence"] = {"count": intel_count, "titles": intel_titles[:10]}
    base["related_timeline"] = {"count": timeline_count}
    base["related_investigations"] = related_investigations

    # Entity roles from node features
    for (etype_attr, eid_attr), label in (
        (("from_entity_type", "from_entity_id"), "from"),
        (("to_entity_type", "to_entity_id"), "to"),
    ):
        etype = getattr(row, etype_attr)
        eid = getattr(row, eid_attr)
        feat = db.scalar(
            select(RelationshipNodeFeature).where(
                RelationshipNodeFeature.entity_type == etype,
                RelationshipNodeFeature.entity_id == eid,
            )
        )
        if feat:
            base[f"{label}_role"] = feat.graph_role
            base[f"{label}_verification"] = feat.verification

    return base


# ---------------------------------------------------------------------------
# §100 Role vocabulary
# ---------------------------------------------------------------------------

@router.get("/relationships/roles", dependencies=_READ, summary="Graph node role vocabulary")
def relationship_roles() -> dict:
    return {"count": len(_CANONICAL_ROLES), "roles": list(_CANONICAL_ROLES)}


# ---------------------------------------------------------------------------
# List relationships (with graph filters §426)
# ---------------------------------------------------------------------------

@router.get("/relationships", dependencies=_READ, summary="List entity relationships")
def list_relationships(
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    relationship_type: Annotated[str | None, Query()] = None,
    verification: Annotated[str | None, Query()] = None,
    confidence_min: Annotated[float | None, Query(ge=0, le=1)] = None,
    include_deleted: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    stmt = select(EntityRelationship).join(RelationshipType)
    if not include_deleted:
        stmt = stmt.where(EntityRelationship.deleted_at.is_(None))
    if entity_type and entity_id:
        stmt = stmt.where(
            (EntityRelationship.from_entity_type == entity_type.upper())
            & (EntityRelationship.from_entity_id == entity_id)
            | (EntityRelationship.to_entity_type == entity_type.upper())
            & (EntityRelationship.to_entity_id == entity_id)
        )
    if relationship_type:
        stmt = stmt.where(RelationshipType.name == relationship_type.upper())
    if verification:
        stmt = stmt.where(EntityRelationship.verification == verification.upper())
    if confidence_min is not None:
        stmt = stmt.where(EntityRelationship.confidence >= confidence_min)
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


# ---------------------------------------------------------------------------
# Relationship-type vocabulary
# ---------------------------------------------------------------------------

@router.get("/relationships/types", dependencies=_READ, summary="Relationship-type vocabulary")
def relationship_types(db: Session = Depends(get_db), limit: Annotated[int, Query(ge=1, le=200)] = 200) -> dict:
    rows = db.scalars(
        select(RelationshipType).order_by(RelationshipType.name).limit(min(max(limit, 1), 200))
    ).all()
    return {
        "count": len(rows),
        "types": [{"name": t.name, "description": t.description} for t in rows],
    }


# ---------------------------------------------------------------------------
# §103 Enriched detail
# ---------------------------------------------------------------------------

@router.get("/relationships/{relationship_id}", dependencies=_READ, summary="Relationship detail with provenance")
def relationship_detail(relationship_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    row = db.get(EntityRelationship, relationship_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    names = _resolve_for_rows(db, [row])
    return _enrich_detail(db, row, names)


# ---------------------------------------------------------------------------
# §107 Node creation
# ---------------------------------------------------------------------------

class NodeBody(BaseModel):
    entity_type: str
    name: str
    external_ref: str | None = None
    graph_role: str | None = None
    sport: str | None = None
    country: str | None = None
    city: str | None = None
    event_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    level: str | None = None
    source_type: str | None = None
    reliability: str | None = None


@router.post("/relationships/nodes", dependencies=_CREATE, summary="Create a graph node (new entity)")
def create_node(
    body: NodeBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """§106/§107: create a new entity node in the graph."""
    kind = body.entity_type.upper()
    if kind not in SUBJECT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported entity type {kind!r}; expected one of {', '.join(SUBJECT_TYPES)}",
        )

    if body.graph_role and body.graph_role.upper() not in _CANONICAL_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Role {body.graph_role!r} not in vocabulary; use one of {', '.join(_CANONICAL_ROLES)}",
        )

    model = _ENTITY_MODELS[kind]
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")

    # Create the entity in the appropriate table
    entity_id = uuid.uuid4()
    if kind == "ATHLETE":
        parts = name.split(None, 1)
        entity = Athlete(
            id=entity_id,
            external_ref=body.external_ref or f"ATH-{entity_id.hex[:8].upper()}",
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else parts[0],
            sport=body.sport,
            nationality=body.country,
            status="ACTIVE",
        )
    elif kind == "TEAM":
        entity = Team(id=entity_id, external_ref=body.external_ref, name=name, country=body.country, status="ACTIVE")
    elif kind == "ORGANIZATION":
        entity = Organization(id=entity_id, external_ref=body.external_ref, name=name, country=body.country, status="ACTIVE")
    elif kind == "PROVIDER":
        entity = Provider(id=entity_id, external_ref=body.external_ref, name=name, country=body.country, status="ACTIVE")
    elif kind == "SUPPORT_PERSON":
        entity = SupportPerson(id=entity_id, external_ref=body.external_ref, name=name, country=body.country, status="ACTIVE")
    elif kind == "SUPPLEMENT":
        entity = Supplement(id=entity_id, external_ref=body.external_ref, name=name, status="ACTIVE")
    elif kind == "EVENT":
        sd = date.fromisoformat(body.start_date) if body.start_date else None
        ed = date.fromisoformat(body.end_date) if body.end_date else None
        entity = Event(id=entity_id, external_ref=body.external_ref, name=name,
                       event_type=body.event_type, location=body.location,
                       start_date=sd, end_date=ed, status="ACTIVE")
    elif kind == "COMPETITION":
        sd = date.fromisoformat(body.start_date) if body.start_date else None
        ed = date.fromisoformat(body.end_date) if body.end_date else None
        entity = Competition(id=entity_id, external_ref=body.external_ref, name=name,
                             sport=body.sport, level=body.level, location=body.location,
                             start_date=sd, end_date=ed, status="ACTIVE")
    elif kind == "LOCATION":
        entity = Location(id=entity_id, external_ref=body.external_ref, name=name,
                          country=body.country, city=body.city,
                          location_type=body.event_type, status="ACTIVE")
    elif kind == "SOURCE":
        entity = Source(id=entity_id, external_ref=body.external_ref, name=name,
                        source_type=body.source_type, reliability=body.reliability,
                        status="ACTIVE")
    else:
        raise HTTPException(status_code=422, detail=f"Unhandled entity type {kind}")

    db.add(entity)
    db.flush()

    # Node feature row (role + verification)
    feat = RelationshipNodeFeature(
        entity_type=kind,
        entity_id=entity_id,
        graph_role=body.graph_role.upper() if body.graph_role else None,
        verification="UNVERIFIED",
    )
    db.add(feat)
    db.flush()

    record_audit(
        db, actor_id=user.id,
        action="GRAPH_NODE_CREATED",
        entity_type="GRAPH_NODE",
        entity_id=str(entity_id),
        metadata={"entity_type": kind, "name": name, "graph_role": feat.graph_role},
    )
    db.commit()

    return {
        "id": str(entity_id),
        "entity_type": kind,
        "name": name,
        "external_ref": getattr(entity, "external_ref", None),
        "graph_role": feat.graph_role,
        "verification": feat.verification,
    }


# ---------------------------------------------------------------------------
# Node detail (§427/§428)
# ---------------------------------------------------------------------------

@router.get("/relationships/nodes/{entity_type}/{entity_id}", dependencies=_READ, summary="Node detail with relationships and counts")
def node_detail(entity_type: str, entity_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    kind = entity_type.upper()
    model = _ENTITY_MODELS.get(kind)
    if model is None:
        raise HTTPException(status_code=422, detail=f"Unsupported entity type {kind!r}")
    entity = db.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{kind} entity not found")

    name = resolve_names(db, [(kind, entity_id)]).get((kind, str(entity_id)), str(entity_id)[:8])

    # Relationships involving this node
    rels = db.scalars(
        select(EntityRelationship).where(
            EntityRelationship.deleted_at.is_(None),
            (EntityRelationship.from_entity_type == kind) & (EntityRelationship.from_entity_id == entity_id)
            | (EntityRelationship.to_entity_type == kind) & (EntityRelationship.to_entity_id == entity_id),
        )
    ).all()
    rel_names = _resolve_for_rows(db, rels)
    relationships = [_relationship_summary(r, rel_names) for r in rels]

    # Degree = unique neighbors
    neighbors: set[tuple[str, str]] = set()
    for r in rels:
        if r.from_entity_type == kind:
            neighbors.add((r.to_entity_type, str(r.to_entity_id)))
        else:
            neighbors.add((r.from_entity_type, str(r.from_entity_id)))

    # Intelligence linked
    intel_count = db.scalar(
        select(func.count()).select_from(IntelligenceReport).where(
            IntelligenceReport.subject_type == kind,
            IntelligenceReport.subject_id == entity_id,
        )
    ) or 0

    # Investigations linked
    inv_count = db.scalar(
        select(func.count()).select_from(Investigation).where(
            Investigation.subject_type == kind,
            Investigation.subject_id == entity_id,
        )
    ) or 0

    # Node feature
    feat = db.scalar(
        select(RelationshipNodeFeature).where(
            RelationshipNodeFeature.entity_type == kind,
            RelationshipNodeFeature.entity_id == entity_id,
        )
    )

    return {
        "id": str(entity_id),
        "entity_type": kind,
        "name": name,
        "graph_role": feat.graph_role if feat else None,
        "verification": feat.verification if feat else None,
        "notes": feat.notes if feat else None,
        "degree": len(neighbors),
        "neighbor_count": len(neighbors),
        "relationship_count": len(relationships),
        "intelligence_count": intel_count,
        "investigation_count": inv_count,
        "relationships": relationships,
    }


# ---------------------------------------------------------------------------
# Node position persistence (§553)
# ---------------------------------------------------------------------------

class PositionBody(BaseModel):
    x: float
    y: float


class NodeFeatureBody(BaseModel):
    graph_role: str | None = None
    verification: str | None = None
    notes: str | None = None


@router.patch("/relationships/nodes/{entity_type}/{entity_id}/position", dependencies=_MODIFY, summary="Persist node position")
def update_node_position(
    entity_type: str, entity_id: uuid.UUID,
    body: PositionBody,
    db: Session = Depends(get_db),
) -> dict:
    """§553: persist user-adjusted node positions separately from truth."""
    kind = entity_type.upper()
    if kind not in SUBJECT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported entity type {kind!r}")

    feat = db.scalar(
        select(RelationshipNodeFeature).where(
            RelationshipNodeFeature.entity_type == kind,
            RelationshipNodeFeature.entity_id == entity_id,
        )
    )
    if feat is None:
        feat = RelationshipNodeFeature(entity_type=kind, entity_id=entity_id)
        db.add(feat)
    feat.position_x = body.x
    feat.position_y = body.y
    db.commit()
    return {"ok": True, "entity_type": kind, "entity_id": str(entity_id), "x": body.x, "y": body.y}


@router.patch("/relationships/nodes/{entity_type}/{entity_id}/features", dependencies=_MODIFY, summary="Update node role/verification")
@router.patch("/relationships/nodes/{entity_type}/{entity_id}", dependencies=_MODIFY, summary="Update node role/verification/notes")
def update_node_features(
    entity_type: str, entity_id: uuid.UUID,
    body: NodeFeatureBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    kind = entity_type.upper()
    if kind not in SUBJECT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported entity type {kind!r}")
    if body.graph_role and body.graph_role.upper() not in _CANONICAL_ROLES:
        raise HTTPException(status_code=422, detail=f"Role {body.graph_role!r} not in vocabulary")

    feat = db.scalar(
        select(RelationshipNodeFeature).where(
            RelationshipNodeFeature.entity_type == kind,
            RelationshipNodeFeature.entity_id == entity_id,
        )
    )
    if feat is None:
        feat = RelationshipNodeFeature(entity_type=kind, entity_id=entity_id)
        db.add(feat)

    if body.graph_role is not None:
        feat.graph_role = body.graph_role.upper() if body.graph_role else None
    if body.verification is not None:
        feat.verification = body.verification.upper() if body.verification else None
    if body.notes is not None:
        feat.notes = body.notes

    db.commit()
    return {
        "ok": True,
        "entity_type": kind,
        "entity_id": str(entity_id),
        "graph_role": feat.graph_role,
        "verification": feat.verification,
    }


# ---------------------------------------------------------------------------
# §98 Create relationship (existing — enhanced with frequency/notes/verification)
# ---------------------------------------------------------------------------

class RelationshipBody(BaseModel):
    from_entity_type: str
    from_entity_id: uuid.UUID
    to_entity_type: str
    to_entity_id: uuid.UUID
    relationship_type: str
    start_date: date | None = None
    end_date: date | None = None
    confidence: float | None = None
    source_id: uuid.UUID | None = None
    frequency: str | None = None
    notes: str | None = None
    verification: str | None = None


@router.post("/relationships", dependencies=_CREATE, summary="Record a relationship manually")
def create_relationship(
    body: RelationshipBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Manual association between two existing entities. Descriptive only:
    recorded context for the case team, never an assertion of wrongdoing."""
    from_type = body.from_entity_type.upper()
    to_type = body.to_entity_type.upper()
    for entity_type in (from_type, to_type):
        if entity_type not in SUBJECT_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported entity type {entity_type!r}; expected one of {', '.join(SUBJECT_TYPES)}",
            )
    if from_type == to_type and body.from_entity_id == body.to_entity_id:
        raise HTTPException(status_code=422, detail="An entity cannot be related to itself")

    for entity_type, entity_id in ((from_type, body.from_entity_id), (to_type, body.to_entity_id)):
        if not _entity_exists(db, entity_type, entity_id):
            raise HTTPException(
                status_code=422,
                detail=f"{entity_type} entity {entity_id} does not exist",
            )

    confidence = body.confidence
    if confidence is not None and not (0.0 <= confidence <= 1.0):
        raise HTTPException(status_code=422, detail="confidence must be between 0 and 1")

    if body.source_id is not None and db.get(IntelligenceSource, body.source_id) is None:
        raise HTTPException(status_code=422, detail="Referenced intelligence source does not exist")

    rel_type = _ensure_relationship_type(db, body.relationship_type)

    existing = db.scalar(
        select(EntityRelationship).where(
            EntityRelationship.from_entity_type == from_type,
            EntityRelationship.from_entity_id == body.from_entity_id,
            EntityRelationship.to_entity_type == to_type,
            EntityRelationship.to_entity_id == body.to_entity_id,
            EntityRelationship.relationship_type_id == rel_type.id,
            EntityRelationship.deleted_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="This relationship is already recorded")

    row = EntityRelationship(
        from_entity_type=from_type,
        from_entity_id=body.from_entity_id,
        relationship_type_id=rel_type.id,
        to_entity_type=to_type,
        to_entity_id=body.to_entity_id,
        start_date=body.start_date,
        end_date=body.end_date,
        confidence=confidence,
        source_id=body.source_id,
        frequency=body.frequency,
        notes=body.notes,
        verification=body.verification.upper() if body.verification else None,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        actor_id=user.id,
        action="RELATIONSHIP_CREATED",
        entity_type="RELATIONSHIP",
        entity_id=str(row.id),
        metadata={
            "relationship_type": rel_type.name,
            "from_entity_type": from_type,
            "from_entity_id": str(body.from_entity_id),
            "to_entity_type": to_type,
            "to_entity_id": str(body.to_entity_id),
            "confidence": confidence,
        },
    )
    db.commit()
    db.refresh(row, ["rel_type"])
    names = resolve_names(
        db,
        [(row.from_entity_type, row.from_entity_id), (row.to_entity_type, row.to_entity_id)],
    )
    return _relationship_summary(row, names)


# ---------------------------------------------------------------------------
# §105/§108 Edit + soft-delete relationships
# ---------------------------------------------------------------------------

class RelationshipUpdateBody(BaseModel):
    relationship_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    confidence: float | None = None
    source_id: uuid.UUID | None = None
    frequency: str | None = None
    notes: str | None = None
    verification: str | None = None


@router.patch("/relationships/{relationship_id}", dependencies=_MODIFY, summary="Edit a relationship")
def update_relationship(
    relationship_id: uuid.UUID,
    body: RelationshipUpdateBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    row = db.get(EntityRelationship, relationship_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Relationship not found")

    if body.relationship_type is not None:
        row.rel_type = _ensure_relationship_type(db, body.relationship_type)
    if body.start_date is not None:
        row.start_date = body.start_date
    if body.end_date is not None:
        row.end_date = body.end_date
    if body.confidence is not None:
        if not (0.0 <= body.confidence <= 1.0):
            raise HTTPException(status_code=422, detail="confidence must be between 0 and 1")
        row.confidence = body.confidence
    if body.source_id is not None:
        if db.get(IntelligenceSource, body.source_id) is None:
            raise HTTPException(status_code=422, detail="Referenced intelligence source does not exist")
        row.source_id = body.source_id
    if body.frequency is not None:
        row.frequency = body.frequency
    if body.notes is not None:
        row.notes = body.notes
    if body.verification is not None:
        row.verification = body.verification.upper() if body.verification else None

    db.flush()
    record_audit(
        db, actor_id=user.id,
        action="RELATIONSHIP_UPDATED",
        entity_type="RELATIONSHIP",
        entity_id=str(row.id),
        metadata={"fields": [k for k, v in body.model_dump().items() if v is not None]},
    )
    db.commit()
    db.refresh(row, ["rel_type"])
    names = resolve_names(
        db,
        [(row.from_entity_type, row.from_entity_id), (row.to_entity_type, row.to_entity_id)],
    )
    return _relationship_summary(row, names)


@router.delete("/relationships/{relationship_id}", dependencies=_MODIFY, summary="Soft-delete a relationship")
def delete_relationship(
    relationship_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """§105 soft-delete: mark as deleted, never physically remove."""
    row = db.get(EntityRelationship, relationship_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Relationship not found")

    row.deleted_at = datetime.utcnow()
    db.flush()
    record_audit(
        db, actor_id=user.id,
        action="RELATIONSHIP_DELETED",
        entity_type="RELATIONSHIP",
        entity_id=str(row.id),
    )
    db.commit()
    return {"ok": True, "id": str(relationship_id), "status": "DELETED"}


# ---------------------------------------------------------------------------
# §109 Node features for graph (bulk positions)
# ---------------------------------------------------------------------------

@router.get("/relationships/nodes/features", dependencies=_READ, summary="Bulk node features (positions, roles)")
def list_node_features(
    entity_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(RelationshipNodeFeature)
    if entity_type:
        stmt = stmt.where(RelationshipNodeFeature.entity_type == entity_type.upper())
    rows = db.scalars(stmt.limit(min(max(limit, 1), 500))).all()
    return {
        "count": len(rows),
        "features": [
            {
                "entity_type": f.entity_type,
                "entity_id": str(f.entity_id),
                "graph_role": f.graph_role,
                "verification": f.verification,
                "position_x": f.position_x,
                "position_y": f.position_y,
            }
            for f in rows
        ],
    }
