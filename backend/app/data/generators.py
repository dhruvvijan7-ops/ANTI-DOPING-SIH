"""Deterministic generators for the synthetic scenario runtime (G2).

Generation is fully deterministic: the same seed plus the same reference date
produces identical entities, ids, event offsets and orders. Each logical grid of
random choice uses its own per-key PRNG so adding a field elsewhere never shifts
anyone else's values. All records are synthetic and clearly labeled (SYN- refs).
"""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.data.registry import (
    SCENARIO_CORRELATED_ANOMALY,
    SCENARIO_FALSE_POSITIVE,
    SCENARIO_ISOLATED_ANOMALY,
    SCENARIO_MULTI_SOURCE,
    SCENARIO_NETWORK,
    SCENARIO_NORMAL,
    SCENARIO_TEMPORAL,
    ScenarioSpec,
)
from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.intelligence import IntelligenceReport, IntelligenceSource
from app.models.relationships import EntityRelationship
from app.models.subjects import Athlete, Organization, Provider, Supplement, SupportPerson, Team

# --------------------------------------------------------------------------- pools

FIRST_NAMES = [
    "Aya", "Liam", "Sofia", "Noah", "Emma", "Kai", "Mina", "Tomas", "Iara", "Ravi",
    "Lena", "Marek", "Zara", "Omar", "Ines", "Felix", "Nadia", "Theo", "Yara", "Eli",
]
LAST_NAMES = [
    "Abramson", "Bechtold", "Cardoso", "Dupont", "Eriksen", "Ferraro", "Garcia",
    "Haddad", "Ivanov", "Jensen", "Kowalski", "Larsen", "Morel", "Nakamura",
    "Okafor", "Purcell", "Quinn", "Rossi", "Santos", "Tanaka",
]
COUNTRIES = ["FR", "DE", "PT", "NO", "IT", "ES", "JP", "NG", "PL", "BR", "DK", "TR"]
CITIES = {
    "FR": "Paris", "DE": "Berlin", "PT": "Lisbon", "NO": "Oslo", "IT": "Rome",
    "ES": "Madrid", "JP": "Osaka", "NG": "Lagos", "PL": "Warsaw", "BR": "Sao Paulo",
    "DK": "Copenhagen", "TR": "Istanbul",
}
SPORTS = {
    "CYCLING": ["ROAD", "TRACK"],
    "SWIMMING": ["FREESTYLE", "BACKSTROKE"],
    "ATHLETICS": ["SPRINT", "MIDDLE_DISTANCE"],
    "WEIGHTLIFTING": ["81KG", "96KG"],
    "JUDO": ["73KG", "90KG"],
}
SUPPORT_ROLES = ["COACH", "PHYSIOTHERAPIST", "TEAM_DOCTOR", "AGENT", "MANAGER", "NUTRITIONIST"]

# (name, source_type, reliability_default, confidentiality)
SOURCE_SPECS = [
    ("NADO-LAB-01", "NADO-TEST", "B", "INTERNAL"),
    ("WADA-ACC-LAB", "WADA-TEST", "A", "INTERNAL"),
    ("ADAMS-PLATFORM", "ADAMS", "C", "INTERNAL"),
    ("CONF-HANDLER-01", "CONFIDENTIAL", "B", "CONFIDENTIAL"),
    ("CONF-HANDLER-02", "CONFIDENTIAL", "C", "CONFIDENTIAL"),
    ("OPEN-SOURCE-MONITOR", "OSINT", "C", "INTERNAL"),
    ("LEO-SHARE", "LEO", "B", "RESTRICTED"),
    ("BORDER-CTRL", "BORDER", "C", "INTERNAL"),
]

RELATIONSHIP_TYPES = [
    "TEAM_MEMBER",
    "TRAINING_PARTNER",
    "COACH_ATHLETE",
    "MEDICAL_STAFF",
    "TRAVEL_COMPANION",
    "SUPPLEMENT_PROVIDER",
]

# --------------------------------------------------------------------------- helpers


class Gen:
    """Deterministic generator context: stable ids/dates/per-key randomness."""

    def __init__(self, seed: int, as_of: date | None = None):
        self.seed = int(seed)
        self.as_of = as_of or date.today()

    def id(self, key: str) -> uuid.UUID:
        return uuid.UUID(int=random.Random(f"{self.seed}:{key}").getrandbits(128))

    def rng(self, key: str) -> random.Random:
        return random.Random(f"{self.seed}:{key}")

    def days_ago(self, key: str, low: int, high: int) -> date:
        return self.as_of - timedelta(days=self.rng(key).randint(low, high))

    def choice(self, key: str, seq: list) -> object:
        return self.rng(key).choice(seq)


@dataclass
class SyntheticSet:
    """In-memory outcome of a scenario generation (persisted by populate.py)."""

    seed: int
    as_of: date
    teams: list[Team] = field(default_factory=list)
    orgs: list[Organization] = field(default_factory=list)
    providers: list[Provider] = field(default_factory=list)
    supplements: list[Supplement] = field(default_factory=list)
    support: list[SupportPerson] = field(default_factory=list)
    athletes: list[Athlete] = field(default_factory=list)
    sources: list[IntelligenceSource] = field(default_factory=list)
    relationships: list[EntityRelationship] = field(default_factory=list)
    testing: list[TestingEvent] = field(default_factory=list)
    biological: list[BiologicalObservation] = field(default_factory=list)
    whereabouts: list[WhereaboutsEvent] = field(default_factory=list)
    travel: list[TravelEvent] = field(default_factory=list)
    medical: list[MedicalEvent] = field(default_factory=list)
    supplement_events: list[SupplementEvent] = field(default_factory=list)
    reports: list[IntelligenceReport] = field(default_factory=list)

    @property
    def target(self) -> Athlete | None:
        return self.athletes[0] if self.athletes else None

    def summary(self) -> dict:
        return {
            "athletes": len(self.athletes),
            "support_persons": len(self.support),
            "sources": len(self.sources),
            "relationships": len(self.relationships),
            "testing_events": len(self.testing),
            "biological_observations": len(self.biological),
            "whereabouts_events": len(self.whereabouts),
            "travel_events": len(self.travel),
            "medical_events": len(self.medical),
            "supplement_events": len(self.supplement_events),
            "intelligence_reports": len(self.reports),
        }

    def source_by_type(self, source_type: str) -> IntelligenceSource | None:
        return next((s for s in self.sources if s.source_type == source_type), None)


def _source_by_type(seth: SyntheticSet, source_type: str) -> IntelligenceSource:
    src = seth.source_by_type(source_type)
    if src is None:
        raise ValueError(f"synthetic source type not present: {source_type}")
    return src


# --------------------------------------------------------------------------- builders


def build_normal_population(g: Gen, n_athletes: int = 14) -> SyntheticSet:
    seth = SyntheticSet(seed=g.seed, as_of=g.as_of)

    for i in range(3):
        country = g.choice(f"team-{i}", COUNTRIES)
        seth.teams.append(
            Team(
                id=g.id(f"team-{i}"),
                external_ref=f"SYN-TEAM-{i:02d}",
                name=f"{country} Elite Track Programme",
                sport=g.choice(f"team-sport-{i}", list(SPORTS)),
                federation=f"{country} Federation",
                country=country,
                status="ACTIVE",
            )
        )
    for i in range(3):
        seth.orgs.append(
            Organization(
                id=g.id(f"org-{i}"),
                external_ref=f"SYN-ORG-{i:02d}",
                name=g.choice(f"org-name-{i}", [f"National Testing Body {i}", f"Regional Lab {i}", f"Integrity Unit {i}"]),
                org_type=g.choice(f"org-type-{i}", ["NADO", "LAB", "FEDERATION"]),
                country=g.choice(f"org-country-{i}", COUNTRIES),
                status="ACTIVE",
            )
        )
    for i in range(3):
        seth.providers.append(
            Provider(
                id=g.id(f"prov-{i}"),
                external_ref=f"SYN-PROV-{i:02d}",
                name=g.choice(f"prov-name-{i}", [f"Distributor {i}", f"Pharma Co {i}", f"Supplier {i}"]),
                provider_type=g.choice(f"prov-type-{i}", ["SUPPLEMENT", "PHARMACEUTICAL", "LAB"]),
                country=g.choice(f"prov-country-{i}", COUNTRIES),
                status="ACTIVE",
            )
        )
    for i in range(4):
        provider = seth.providers[i % len(seth.providers)]
        seth.supplements.append(
            Supplement(
                id=g.id(f"supp-{i}"),
                external_ref=f"SYN-SUPP-{i:02d}",
                name=g.choice(f"supp-name-{i}", [f"Electrolyte Blend {i}", f"Recovery Formula {i}", f"Vitamin Complex {i}", f"Joint Support {i}"]),
                provider_id=provider.id,
                category=g.choice(f"supp-cat-{i}", ["ELECTROLYTES", "PROTEIN", "VITAMINS", "HERBAL"]),
                status="ACTIVE",
            )
        )
    for i in range(8):
        seth.support.append(
            SupportPerson(
                id=g.id(f"sp-{i}"),
                external_ref=f"SYN-SP-{i:02d}",
                name=f"{g.choice(f'sp-first-{i}', FIRST_NAMES)} {g.choice(f'sp-last-{i}', LAST_NAMES)}",
                support_role=g.choice(f"sp-role-{i}", SUPPORT_ROLES),
                organization=seth.orgs[i % len(seth.orgs)].name,
                organization_id=seth.orgs[i % len(seth.orgs)].id,
                country=g.choice(f"sp-country-{i}", COUNTRIES),
                status="ACTIVE",
            )
        )
    for i, (name, source_type, reliability, confidentiality) in enumerate(SOURCE_SPECS):
        seth.sources.append(
            IntelligenceSource(
                id=g.id(f"src:{i}:{source_type}"),
                external_ref=f"SYN-SRC-{source_type}",
                name=name,
                source_type=source_type,
                reliability_default=reliability,
                confidentiality=confidentiality,
                activity=True,
                is_active=True,
            )
        )

    for i in range(n_athletes):
        sport = g.choice(f"ath-sport-{i}", list(SPORTS))
        team = seth.teams[i % len(seth.teams)]
        gender = g.choice(f"ath-gender-{i}", ["M", "F"])
        seth.athletes.append(
            Athlete(
                id=g.id(f"ath-{i}"),
                external_ref=f"SYN-ATH-{i:03d}",
                first_name=g.choice(f"ath-first-{i}", FIRST_NAMES),
                last_name=g.choice(f"ath-last-{i}", LAST_NAMES),
                date_of_birth=g.as_of - timedelta(days=g.rng(f"ath-dob-{i}").randint(7300, 11500)),
                nationality=g.choice(f"ath-nat-{i}", COUNTRIES),
                sport=sport,
                discipline=g.choice(f"ath-disc-{i}", SPORTS[sport]),
                gender=gender,
                team_id=team.id,
                status="ACTIVE",
            )
        )

    lab = _source_by_type(seth, "NADO-TEST")
    adams = _source_by_type(seth, "ADAMS")
    border = _source_by_type(seth, "BORDER")
    conf = _source_by_type(seth, "CONFIDENTIAL")

    for i, athlete in enumerate(seth.athletes):
        _routine_testing(g, i, athlete, seth, lab)
        _routine_biological(g, i, athlete, seth, lab)
        _routine_whereabouts(g, i, athlete, seth, adams)
        _routine_travel(g, i, athlete, seth, border)
        _routine_medical(g, i, athlete, seth, lab)
        _routine_supplement(g, i, athlete, seth, conf)
        _routine_reports(g, i, athlete, seth, conf)

    rel_team = "TEAM_MEMBER"
    rel_coach = "COACH_ATHLETE"
    for i, athlete in enumerate(seth.athletes):
        # each athlete links to one other in the same team, plus a coach
        other = seth.athletes[(i + 1) % len(seth.athletes)]
        seth.relationships.append(
            EntityRelationship(
                id=g.id(f"rel-team-{i}"),
                relationship_type_id=None,  # resolved at persist by name lookup
                from_entity_type="ATHLETE",
                from_entity_id=athlete.id,
                to_entity_type="ATHLETE",
                to_entity_id=other.id,
                start_date=g.as_of - timedelta(days=g.rng(f"rel-start-{i}").randint(100, 600)),
                confidence=round(g.rng(f"rel-conf-{i}").uniform(0.4, 0.9), 2),
                source_id=conf.id,
            )
        )
        seth.relationships[-1]._rel_type_name = rel_team  # type: ignore[attr-defined]
        coach = seth.support[i % len(seth.support)]
        seth.relationships.append(
            EntityRelationship(
                id=g.id(f"rel-coach-{i}"),
                relationship_type_id=None,
                from_entity_type="SUPPORT_PERSON",
                from_entity_id=coach.id,
                to_entity_type="ATHLETE",
                to_entity_id=athlete.id,
                start_date=g.as_of - timedelta(days=150),
                confidence=1.0,
                source_id=conf.id,
            )
        )
        seth.relationships[-1]._rel_type_name = rel_coach  # type: ignore[attr-defined]

    # collate unique relationship type names used so persist can create them
    return seth


def _routine_testing(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, lab: IntelligenceSource) -> None:
    rnd = g.rng(f"tests-{i}")
    for j in range(rnd.randint(2, 5)):
        seth.testing.append(
            TestingEvent(
                id=g.id(f"test-{i}-{j}"),
                athlete_id=athlete.id,
                test_date=seth.as_of - timedelta(days=rnd.randint(30, 420)),
                test_type=rnd.choice(["OUT_OF_COMPETITION", "COMPETITION"]),
                location=rnd.choice(list(CITIES.values())),
                result_classification="NEGATIVE",
                source_id=lab.id,
            )
        )


def _routine_biological(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, lab: IntelligenceSource) -> None:
    rnd = g.rng(f"bio-{i}")
    for j in range(rnd.randint(0, 2)):
        marker = rnd.choice(["RET", "HCT", "OFF"])
        seth.biological.append(
            BiologicalObservation(
                id=g.id(f"bio-{i}-{j}"),
                athlete_id=athlete.id,
                observation_date=seth.as_of - timedelta(days=rnd.randint(40, 300)),
                marker=marker,
                value=round(rnd.uniform(0.1, 1.4), 1),
                unit="RATIO",
                baseline_deviation=round(rnd.uniform(0.1, 1.6), 1),
                source_id=lab.id,
            )
        )


def _routine_whereabouts(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, adams: IntelligenceSource) -> None:
    rnd = g.rng(f"wh-{i}")
    for j in range(rnd.randint(0, 2)):
        status = rnd.choice(["FULFILLED", "FINE", "REPORTED"])
        seth.whereabouts.append(
            WhereaboutsEvent(
                id=g.id(f"wh-{i}-{j}"),
                athlete_id=athlete.id,
                event_date=seth.as_of - timedelta(days=rnd.randint(30, 300)),
                event_type="FILING",
                expected_location=rnd.choice(list(CITIES.values())),
                observed_location=rnd.choice(list(CITIES.values())),
                status=status,
                source_id=adams.id,
            )
        )


def _routine_travel(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, border: IntelligenceSource) -> None:
    rnd = g.rng(f"travel-{i}")
    for j in range(rnd.randint(0, 2)):
        seth.travel.append(
            TravelEvent(
                id=g.id(f"travel-{i}-{j}"),
                athlete_id=athlete.id,
                event_date=seth.as_of - timedelta(days=rnd.randint(40, 350)),
                origin=rnd.choice(list(CITIES.values())),
                destination=rnd.choice(list(CITIES.values())),
                event_type=rnd.choice(["DOMESTIC", "INTERNATIONAL"]),
                source_id=border.id,
            )
        )


def _routine_medical(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, lab: IntelligenceSource) -> None:
    rnd = g.rng(f"med-{i}")
    if rnd.randint(0, 3) == 0:
        seth.medical.append(
            MedicalEvent(
                id=g.id(f"med-{i}"),
                athlete_id=athlete.id,
                event_date=seth.as_of - timedelta(days=rnd.randint(40, 240)),
                event_type=rnd.choice(["TUE_REVIEW", "INJURY_REPORT"]),
                metadata_classification="ROUTINE",
                source_id=lab.id,
            )
        )


def _routine_supplement(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, conf: IntelligenceSource) -> None:
    rnd = g.rng(f"sup-{i}")
    if rnd.randint(0, 2) == 0:
        supplement = seth.supplements[i % len(seth.supplements)]
        seth.supplement_events.append(
            SupplementEvent(
                id=g.id(f"sup-{i}"),
                athlete_id=athlete.id,
                supplement_id=supplement.id,
                event_date=seth.as_of - timedelta(days=rnd.randint(40, 240)),
                usage_note="routine use",
                source_id=conf.id,
            )
        )


def _routine_reports(g: Gen, i: int, athlete: Athlete, seth: SyntheticSet, conf: IntelligenceSource) -> None:
    rnd = g.rng(f"reports-{i}")
    for j in range(rnd.randint(0, 2)):
        seth.reports.append(
            IntelligenceReport(
                id=g.id(f"report-{i}-{j}"),
                source_id=conf.id,
                subject_type="ATHLETE",
                subject_id=athlete.id,
                title=f"General observation {j + 1}",
                description="Routine context note without specific concern.",
                report_date=seth.as_of - timedelta(days=rnd.randint(40, 200)),
                reliability="C",
                information_quality="3",
                confidentiality="INTERNAL",
                status="NEW",
                info_category="GENERAL",
                is_duplicate=False,
            )
        )


# --------------------------------------------------------------------------- scenario signatures


def _apply_isolated_anomaly(seth: SyntheticSet, target: Athlete) -> None:
    lab = _source_by_type(seth, "NADO-TEST")
    day = 12
    seth.testing.append(
        TestingEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-iso-test").getrandbits(128)),
            athlete_id=target.id,
            test_date=seth.as_of - timedelta(days=day),
            test_type="OUT_OF_COMPETITION",
            result_classification="NEGATIVE",
            source_id=lab.id,
        )
    )
    seth.biological.append(
        BiologicalObservation(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-iso-bio").getrandbits(128)),
            athlete_id=target.id,
            observation_date=seth.as_of - timedelta(days=day),
            marker="RET",
            value=4.1,
            unit="RATIO",
            baseline_deviation=4.1,
            source_id=lab.id,
        )
    )


def _apply_temporal(seth: SyntheticSet, target: Athlete) -> None:
    lab = _source_by_type(seth, "NADO-TEST")
    adams = _source_by_type(seth, "ADAMS")
    border = _source_by_type(seth, "BORDER")
    conf = _source_by_type(seth, "CONFIDENTIAL")
    cluster = [2, 4, 5, 7, 9]
    seth.testing.append(
        TestingEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-tmp-test1").getrandbits(128)),
            athlete_id=target.id, test_date=seth.as_of - timedelta(days=cluster[0]),
            test_type="OUT_OF_COMPETITION", result_classification="NEGATIVE", source_id=lab.id,
        )
    )
    seth.whereabouts.append(
        WhereaboutsEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-tmp-wh").getrandbits(128)),
            athlete_id=target.id, event_date=seth.as_of - timedelta(days=cluster[1]),
            event_type="FILING", expected_location="Oslo", observed_location=None,
            status="MISSED", source_id=adams.id,
        )
    )
    seth.travel.append(
        TravelEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-tmp-travel").getrandbits(128)),
            athlete_id=target.id, event_date=seth.as_of - timedelta(days=cluster[2]),
            origin="Oslo", destination="Tokyo", event_type="INTERNATIONAL", source_id=border.id,
        )
    )
    seth.supplement_events.append(
        SupplementEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-tmp-supp").getrandbits(128)),
            athlete_id=target.id, supplement_id=seth.supplements[0].id,
            event_date=seth.as_of - timedelta(days=cluster[3]), usage_note="imported product",
            source_id=conf.id,
        )
    )
    seth.testing.append(
        TestingEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-tmp-test2").getrandbits(128)),
            athlete_id=target.id, test_date=seth.as_of - timedelta(days=cluster[4]),
            test_type="OUT_OF_COMPETITION", result_classification="NEGATIVE", source_id=lab.id,
        )
    )


def _apply_network(seth: SyntheticSet, target: Athlete) -> None:
    conf = _source_by_type(seth, "CONFIDENTIAL")
    lab = _source_by_type(seth, "NADO-TEST")
    # dense local network with moderately active connected subjects
    for idx in range(1, 9):
        other = seth.athletes[idx]
        seth.relationships.append(
            EntityRelationship(
                id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-net-{idx}").getrandbits(128)),
                relationship_type_id=None,
                from_entity_type="ATHLETE",
                from_entity_id=target.id,
                to_entity_type="ATHLETE",
                to_entity_id=other.id,
                start_date=seth.as_of - timedelta(days=200),
                confidence=0.95,
                source_id=conf.id,
            )
        )
        seth.relationships[-1]._rel_type_name = "TRAINING_PARTNER"  # type: ignore[attr-defined]
    # give connected athletes moderate recent activity so their provisional scores rise
    for idx in range(1, 9):
        other = seth.athletes[idx]
        for j, days in enumerate((5, 12, 20)):
            seth.testing.append(
                TestingEvent(
                    id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-con-test-{idx}-{j}").getrandbits(128)),
                    athlete_id=other.id,
                    test_date=seth.as_of - timedelta(days=days),
                    test_type="COMPETITION",
                    result_classification="NEGATIVE",
                    source_id=lab.id,
                )
            )
        for src_name, rel in (("CONFIDENTIAL", "B"), ("OSINT", "C")):
            src = _source_by_type(seth, src_name)
            seth.reports.append(
                IntelligenceReport(
                    id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-con-rep-{idx}-{rel}").getrandbits(128)),
                    source_id=src.id,
                    subject_type="ATHLETE",
                    subject_id=other.id,
                    title="Context on training group",
                    report_date=seth.as_of - timedelta(days=15),
                    reliability=rel,
                    information_quality="2",
                    confidentiality="INTERNAL",
                    status="NEW",
                    info_category="GENERAL",
                    is_duplicate=False,
                )
            )


def _apply_multi_source(seth: SyntheticSet, target: Athlete) -> None:
    # five independent source categories corroborate one information category
    for i, (src_type, rel, days) in enumerate(
        (
            ("NADO-TEST", "B", 12),
            ("OSINT", "C", 18),
            ("LEO", "B", 9),
            ("CONFIDENTIAL", "B", 14),
            ("WADA-TEST", "A", 6),
        )
    ):
        src = _source_by_type(seth, src_type)
        seth.reports.append(
            IntelligenceReport(
                id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-ms-{i}").getrandbits(128)),
                source_id=src.id,
                subject_type="ATHLETE",
                subject_id=target.id,
                title=f"Corroborating report {i + 1}",
                report_date=seth.as_of - timedelta(days=days),
                reliability=rel,
                information_quality="2",
                confidentiality="INTERNAL",
                status="NEW",
                info_category="SUSPECTED_SUBSTANCE_EXPOSURE",
                is_duplicate=False,
            )
        )


def _apply_correlated_anomaly(seth: SyntheticSet, target: Athlete) -> None:
    lab = _source_by_type(seth, "NADO-TEST")
    adams = _source_by_type(seth, "ADAMS")
    conf = _source_by_type(seth, "CONFIDENTIAL")
    _apply_multi_source(seth, target)
    seth.biological.append(
        BiologicalObservation(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-corr-bio1").getrandbits(128)),
            athlete_id=target.id,
            observation_date=seth.as_of - timedelta(days=10),
            marker="RET", value=3.8, unit="RATIO", baseline_deviation=3.8, source_id=lab.id,
        )
    )
    seth.biological.append(
        BiologicalObservation(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-corr-bio2").getrandbits(128)),
            athlete_id=target.id,
            observation_date=seth.as_of - timedelta(days=10),
            marker="HCT", value=3.2, unit="RATIO", baseline_deviation=3.2, source_id=lab.id,
        )
    )
    for j, days in enumerate((3, 6, 8)):
        seth.whereabouts.append(
            WhereaboutsEvent(
                id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-corr-wh-{j}").getrandbits(128)),
                athlete_id=target.id,
                event_date=seth.as_of - timedelta(days=days),
                event_type="FILING",
                expected_location="Berlin",
                observed_location=None,
                status="MISSED" if j == 0 else "REPORTED",
                source_id=adams.id,
            )
        )
    for idx in (1, 2, 3):
        other = seth.athletes[idx]
        seth.relationships.append(
            EntityRelationship(
                id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-corr-rel-{idx}").getrandbits(128)),
                relationship_type_id=None,
                from_entity_type="ATHLETE",
                from_entity_id=target.id,
                to_entity_type="ATHLETE",
                to_entity_id=other.id,
                start_date=seth.as_of - timedelta(days=180),
                confidence=0.9,
                source_id=conf.id,
            )
        )
        seth.relationships[-1]._rel_type_name = "TEAM_MEMBER"  # type: ignore[attr-defined]


def _apply_false_positive(seth: SyntheticSet, target: Athlete) -> None:
    lab = _source_by_type(seth, "NADO-TEST")
    day = 20
    seth.testing.append(
        TestingEvent(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-fp-test").getrandbits(128)),
            athlete_id=target.id,
            test_date=seth.as_of - timedelta(days=day),
            test_type="OUT_OF_COMPETITION",
            result_classification="NEGATIVE",
            source_id=lab.id,
        )
    )
    seth.biological.append(
        BiologicalObservation(
            id=uuid.UUID(int=random.Random(f"{seth.seed}:sig-fp-bio").getrandbits(128)),
            athlete_id=target.id,
            observation_date=seth.as_of - timedelta(days=day),
            marker="HCT",
            value=4.5,
            unit="RATIO",
            baseline_deviation=4.5,
            source_id=lab.id,
        )
    )


_SIGNATURES = {
    SCENARIO_NORMAL: lambda *_: None,
    SCENARIO_ISOLATED_ANOMALY: _apply_isolated_anomaly,
    SCENARIO_TEMPORAL: _apply_temporal,
    SCENARIO_NETWORK: _apply_network,
    SCENARIO_MULTI_SOURCE: _apply_multi_source,
    SCENARIO_CORRELATED_ANOMALY: _apply_correlated_anomaly,
    SCENARIO_FALSE_POSITIVE: _apply_false_positive,
}


def build_scenario(
    spec: ScenarioSpec, seed: int | None = None, as_of: date | None = None
) -> SyntheticSet:
    """Build the full synthetic dataset for a scenario, in memory."""
    effective_seed = spec.default_seed if seed is None else seed
    g = Gen(effective_seed, as_of=as_of)
    seth = build_normal_population(g, n_athletes=14)
    target = seth.target
    if target is not None and spec.ref in _SIGNATURES:
        _SIGNATURES[spec.ref](seth, target)
    seth.rel_type_names = sorted(
        {
            getattr(r, "_rel_type_name", None)
            for r in seth.relationships
            if getattr(r, "_rel_type_name", None)
        }
    )
    return seth