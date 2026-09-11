"""ORM model registry. Import all models so Alembic autogenerate can see them."""
from app.models.analytics import (
    Alert,
    AlertSignal,
    AnalysisRun,
    AnomalyResult,
    CorrelationResult,
    FeatureSnapshot,
    FeatureVersion,
    NetworkResult,
    PriorityScore,
    RuleResult,
    RuleVersion,
)
from app.models.audit import AuditEvent
from app.models.events import (
    BiologicalObservation,
    MedicalEvent,
    SupplementEvent,
    TestingEvent,
    TravelEvent,
    WhereaboutsEvent,
)
from app.models.identity import Permission, Role, User, role_permissions
from app.models.imports import DataImport, ImportRow
from app.models.intelligence import (
    IntelligenceReport,
    IntelligenceSource,
    IntelligenceTag,
    SourceAssessment,
    report_tags,
)
from app.models.investigations import (
    EvidenceItem,
    EvidenceVersion,
    Finding,
    FindingEvidenceLink,
    Investigation,
    InvestigationNote,
    InvestigationTask,
)
from app.models.relationships import (
    EntityRelationship,
    RelationshipType,
    SUBJECT_TYPES as RELATIONSHIP_SUBJECT_TYPES,
)
from app.models.reports import InvestigationReport
from app.models.scenarios import SyntheticScenario
from app.models.subjects import (
    Athlete,
    Organization,
    Provider,
    Supplement,
    SupportPerson,
    SupportPersonAthleteLink,
    Team,
)

__all__ = [
    "Alert",
    "AlertSignal",
    "AnalysisRun",
    "AnomalyResult",
    "Athlete",
    "CorrelationResult",
    "DataImport",
    "FeatureSnapshot",
    "FeatureVersion",
    "ImportRow",
    "IntelligenceReport",
    "NetworkResult",
    "PriorityScore",
    "RuleResult",
    "RuleVersion",
    "AuditEvent",
    "BiologicalObservation",
    "EntityRelationship",
    "EvidenceItem",
    "EvidenceVersion",
    "Finding",
    "FindingEvidenceLink",
    "IntelligenceReport",
    "IntelligenceSource",
    "IntelligenceTag",
    "Investigation",
    "InvestigationNote",
    "InvestigationReport",
    "InvestigationTask",
    "MedicalEvent",
    "Organization",
    "Permission",
    "Provider",
    "RelationshipType",
    "Role",
    "SourceAssessment",
    "SyntheticScenario",
    "Supplement",
    "SupplementEvent",
    "SupportPerson",
    "SupportPersonAthleteLink",
    "Team",
    "TestingEvent",
    "TravelEvent",
    "User",
    "WhereaboutsEvent",
    "report_tags",
    "role_permissions",
]
