"""Analytics stage (D/E): analysis runs, feature/rule catalogs, per-subject results,
priority scores and alerts.

Everything recorded here is an investigative lead (spec stage 1-11). An alert is a
cue for human review; it never asserts that a violation occurred.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="RUNNING", nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), default="ISOLATION_FOREST", nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    feature_version: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class FeatureVersion(Base):
    """Versioned catalog entry for a computed feature."""

    __tablename__ = "feature_versions"
    __table_args__ = (Index("ix_feature_version_id", "identifier", "version", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_fields_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class RuleVersion(Base):
    """Versioned catalog entry for a (possibly disabled) detection rule."""

    __tablename__ = "rule_versions"
    __table_args__ = (Index("ix_rule_version_id", "rule_id", "version", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conditions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        Index("ix_feature_snap_run_subj", "analysis_run_id", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    feature_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feature_version: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RuleResult(Base):
    __tablename__ = "rule_results"
    __table_args__ = (
        Index("ix_rule_results_run_subj", "analysis_run_id", "subject_type", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expression: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"
    __table_args__ = (
        Index("ix_anomaly_run_subj", "analysis_run_id", "subject_type", "subject_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contribution_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_version: Mapped[int] = mapped_column(Integer, nullable=False)


class CorrelationResult(Base):
    __tablename__ = "correlation_results"
    __table_args__ = (
        Index(
            "ix_correlation_run_subj",
            "analysis_run_id",
            "correlation_type",
            "subject_type",
            "subject_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    correlation_type: Mapped[str] = mapped_column(String(16), nullable=False)  # TEMPORAL/CROSS_SOURCE
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signal_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class NetworkResult(Base):
    __tablename__ = "network_results"
    __table_args__ = (
        Index("ix_network_run_subj", "analysis_run_id", "subject_type", "subject_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    degree: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weighted_degree: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    relationship_diversity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    connected_priority_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PriorityScore(Base):
    __tablename__ = "priority_scores"
    __table_args__ = (
        Index("ix_priority_run_subj", "analysis_run_id", "subject_type", "subject_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    rule_score: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    correlation_score: Mapped[float] = mapped_column(Float, nullable=False)
    temporal_score: Mapped[float] = mapped_column(Float, nullable=False)
    network_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    components_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_subject", "subject_type", "subject_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    alert_ref: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    priority_score_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("priority_scores.id", ondelete="CASCADE"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="NEW", nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triage_meta_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    signals: Mapped[list["AlertSignal"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )
    investigation: Mapped["Investigation | None"] = relationship(
        "Investigation", foreign_keys=[investigation_id], back_populates="alerts", lazy="selectin"
    )


class AlertSignal(Base):
    """Traceability links: an alert signal maps to a concrete rule/anomaly/correlation
    result row in the same analysis run."""

    __tablename__ = "alert_signals"
    __table_args__ = (Index("ix_alert_signal_alert", "alert_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(String(16), nullable=False)  # RULE/ANOMALY/TEMPORAL/CROSS_SOURCE/NETWORK
    signal_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    contributed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    alert: Mapped[Alert] = relationship(back_populates="signals")