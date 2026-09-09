"""Persistence, reset and registry orchestration for synthetic scenarios (G2).

Persistence is deterministic: ids are assigned at generation time, so the same
scenario/seed/as-of always lands in the database byte-for-byte. Reset is scoped to
the synthetic domain tables used by the scenario runtime.
"""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.data.generators import SyntheticSet, build_scenario
from app.data.registry import (
    BY_REF,
    ScenarioSpec,
    catalog_summary,
    get_spec,
)
from app.models.relationships import EntityRelationship, RelationshipType
from app.models.scenarios import SyntheticScenario

# Tables owned by the synthetic runtime, truncated (with CASCADE) on reset.
RESET_TABLES = [
    "synthetic_scenarios",
    "entity_relationships",
    "relationship_types",
    "testing_events",
    "biological_observations",
    "whereabouts_events",
    "travel_events",
    "medical_events",
    "supplement_events",
    "intelligence_reports",
    "source_assessments",
    "intelligence_tags",
    "intelligence_sources",
    "support_person_athletes",
    "support_personnel",
    "providers",
    "supplements",
    "organizations",
    "teams",
    "athletes",
]


def reset_synthetic(db: Session) -> None:
    """Drop all synthetic-scenario rows (cascading to junction tables)."""
    db.execute(
        text("TRUNCATE " + ", ".join(RESET_TABLES) + " RESTART IDENTITY CASCADE")
    )
    db.commit()


def _ensure_relationship_types(db: Session, seth: SyntheticSet) -> dict[str, RelationshipType]:
    existing = {
        t.name: t for t in db.query(RelationshipType).filter(RelationshipType.name.in_(seth.rel_type_names)).all()
    }
    for name in seth.rel_type_names:
        if name not in existing:
            row = RelationshipType(id=None, name=name)
            db.add(row)
            db.flush()
            existing[name] = row
    return existing


def persist_synthetic_set(db: Session, seth: SyntheticSet) -> None:
    """Persist an in-memory SyntheticSet; relationship types are resolved by name."""
    db.add_all(seth.teams)
    db.add_all(seth.orgs)
    db.add_all(seth.providers)
    db.add_all(seth.supplements)
    db.add_all(seth.support)
    db.add_all(seth.athletes)
    db.add_all(seth.sources)
    db.flush()

    types = _ensure_relationship_types(db, seth)
    for rel in seth.relationships:
        rel.relationship_type_id = types[getattr(rel, "_rel_type_name", None)].id
    db.add_all(seth.relationships)

    db.add_all(seth.testing)
    db.add_all(seth.biological)
    db.add_all(seth.whereabouts)
    db.add_all(seth.travel)
    db.add_all(seth.medical)
    db.add_all(seth.supplement_events)
    db.add_all(seth.reports)
    db.flush()


def register_scenario_row(
    db: Session, spec: ScenarioSpec, seed: int, seth: SyntheticSet
) -> SyntheticScenario:
    target = seth.target
    extra_refs = json.dumps(
        {
            "seed": seed,
            "as_of": seth.as_of.isoformat(),
            "target_ref": target.external_ref if target else None,
            "target_id": str(target.id) if target else None,
            "population_size": len(seth.athletes),
        }
    )
    row = db.query(SyntheticScenario).filter(SyntheticScenario.scenario_ref == spec.ref).one_or_none()
    if row is None:
        row = SyntheticScenario(scenario_ref=spec.ref)
        db.add(row)
    row.scenario_type = spec.scenario_type
    row.label = spec.label
    row.description = spec.description
    row.subject_type = "ATHLETE" if target else None
    row.subject_id = target.id if target else None
    row.extra_refs = extra_refs
    db.flush()
    return row


def seed_registry(db: Session, as_of: date | None = None) -> None:
    """Persist metadata rows for every catalog entry (no scenario data generated)."""
    for spec in BY_REF.values():
        row = db.query(SyntheticScenario).filter(SyntheticScenario.scenario_ref == spec.ref).one_or_none()
        if row is None:
            row = SyntheticScenario(scenario_ref=spec.ref)
            db.add(row)
        row.scenario_type = spec.scenario_type
        row.label = spec.label
        row.description = spec.description
        row.extra_refs = json.dumps(
            {"seed": spec.default_seed, "as_of": (as_of or date.today()).isoformat()}
        )
    db.commit()


def populate(
    db: Session,
    scenario_ref: str,
    seed: int | None = None,
    as_of: date | None = None,
    reset_first: bool = True,
) -> SyntheticScenario:
    """Generate and persist one scenario; reset the synthetic domain first by default."""
    spec = get_spec(scenario_ref)
    if spec is None:
        raise ValueError(
            f"unknown scenario_ref {scenario_ref!r}; known: {list(BY_REF)}"
        )
    if reset_first:
        reset_synthetic(db)
    effective_seed = spec.default_seed if seed is None else seed
    seth = build_scenario(spec, seed=effective_seed, as_of=as_of)
    persist_synthetic_set(db, seth)
    row = register_scenario_row(db, spec, seed=effective_seed, seth=seth)
    db.commit()
    return row


def reproduce(
    db: Session,
    scenario_ref: str,
    seed: int,
    as_of: date | None = None,
) -> SyntheticScenario:
    """Re-persist a scenario with an explicit seed/as-of, guaranteeing reproducibility."""
    return populate(db, scenario_ref, seed=seed, as_of=as_of, reset_first=True)


def list_scenarios() -> list[dict]:
    return catalog_summary()