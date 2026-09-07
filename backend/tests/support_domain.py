"""Deterministic DB seeding shared by integration tests (F/G + H/I)."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.intelligence import IntelligenceReport, IntelligenceSource
from app.models.relationships import EntityRelationship, RelationshipType
from app.models.subjects import Athlete

ALICE = uuid.uuid4()
BOB = uuid.uuid4()
CAROL = uuid.uuid4()
DAN = uuid.uuid4()

TODAY = date.today()


def ago(days: int) -> date:
    return TODAY - timedelta(days=days)


def _source(db: Session, name: str, source_type: str, reliability: str = "C") -> IntelligenceSource:
    src = IntelligenceSource(name=name, source_type=source_type, reliability_default=reliability)
    db.add(src)
    db.flush()
    return src


def _athlete(db: Session, sid: uuid.UUID, external_ref: str) -> Athlete:
    athlete = Athlete(
        id=sid,
        external_ref=external_ref,
        first_name="Test",
        last_name=external_ref,
        sport="CYCLING",
        status="ACTIVE",
    )
    db.add(athlete)
    db.flush()
    return athlete


def seed_domain(db: Session) -> None:
    """Seed 4 athletes (dense anomalous ALICE + quieter controls) with events,
    intelligence reports and relationships. Idempotent within one test session."""
    lab = _source(db, "National Lab", "NADO-TEST", "C")
    conf = _source(db, "Confidential Source", "CONFIDENTIAL", "B")
    osint = _source(db, "Open Source", "OSINT", "C")
    leo = _source(db, "Law Enforcement", "LEO", "C")
    adams = _source(db, "ADAMS", "ADAMS", "C")
    border = _source(db, "Border Control", "BORDER", "C")

    rel_type = RelationshipType(name="TEAM_MEMBER", description="Same team/training group")
    db.add(rel_type)
    db.flush()

    _athlete(db, ALICE, "ATH-ALICE")
    _athlete(db, BOB, "ATH-BOB")
    _athlete(db, CAROL, "ATH-CAROL")
    _athlete(db, DAN, "ATH-DAN")

    def report(subject_id, days, src, category, reliability, title):
        db.add(
            IntelligenceReport(
                source_id=src.id,
                subject_type="ATHLETE",
                subject_id=subject_id,
                title=title,
                report_date=ago(days),
                reliability=reliability,
                information_quality="2",
                info_category=category,
                status="NEW",
                is_duplicate=False,
            )
        )

    # --- ALICE: dense, multi-source, anomalous -------------------------------
    for days in (38, 30, 22):
        db.add(TestingEvent(athlete_id=ALICE, test_date=ago(days), test_type="OUT_OF_COMPETITION", source_id=lab.id))
    db.add(BiologicalObservation(athlete_id=ALICE, observation_date=ago(30), marker="HCT", value=3.1, baseline_deviation=3.1, source_id=lab.id))
    db.add(BiologicalObservation(athlete_id=ALICE, observation_date=ago(29), marker="RET", value=2.9, baseline_deviation=2.9, source_id=lab.id))
    db.add(WhereaboutsEvent(athlete_id=ALICE, event_date=ago(10), event_type="FILING", status="MISSED", source_id=adams.id))
    db.add(TravelEvent(athlete_id=ALICE, event_date=ago(5), origin="LON", destination="LIM", event_type="INTERNATIONAL", source_id=border.id))
    db.add(MedicalEvent(athlete_id=ALICE, event_date=ago(7), event_type="TUE_REVIEW", source_id=lab.id))
    db.add(SupplementEvent(athlete_id=ALICE, event_date=ago(6), usage_note="imported product", source_id=lab.id))
    for days, src in ((20, conf), (18, osint), (16, leo), (12, lab)):
        report(ALICE, days, src, "DOPING", "B", "Suspected doping engagement")
    alice_rels = [BOB, CAROL, DAN]
    for other in alice_rels:
        db.add(EntityRelationship(relationship_type_id=rel_type.id, from_entity_type="ATHLETE", from_entity_id=ALICE,
                                 to_entity_type="ATHLETE", to_entity_id=other, confidence=1.0, source_id=conf.id))

    # --- BOB: moderate activity ---------------------------------------------
    for days in (90, 60, 30, 20, 10):
        db.add(TestingEvent(athlete_id=BOB, test_date=ago(days), test_type="COMPETITION", source_id=lab.id))
    report(BOB, 25, conf, "GENERAL", "C", "General observation")

    # --- CAROL / DAN: routine, low-volume ------------------------------------
    for days in (150, 120, 90):
        db.add(TestingEvent(athlete_id=CAROL, test_date=ago(days), test_type="COMPETITION", source_id=lab.id))
    for days in (160, 130, 100):
        db.add(TestingEvent(athlete_id=DAN, test_date=ago(days), test_type="COMPETITION", source_id=lab.id))
    db.flush()