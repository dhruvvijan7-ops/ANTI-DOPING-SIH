"""Isolation Forest anomaly detection (pipeline stage 7) with feature-level
explanation.

Model settings are fixed and recorded in every run: n_estimators=200,
contamination=0.05, random_state=42 (reproducible for identical input). The anomaly
score is the Isolation Forest decision function rescaled to 0-100 (100 = most
anomalous). Explanations reference the actual computed feature values and their
standardized deviation from the reference population -- never unsupported natural
language.
"""
from __future__ import annotations

import math
import statistics
import uuid
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest

from app.analysis.contracts import AnalysisConfig

DEFAULT_PARAMS = {"n_estimators": 200, "contamination": 0.05, "random_state": 42}


@dataclass
class FeatureContribution:
    feature_id: str
    contribution: float
    std_value: float
    actual_value: float


@dataclass
class AnomalyOutcome:
    subject_id: uuid.UUID
    raw_score: float
    normalized_score: float
    is_anomaly: bool
    contributions: list[FeatureContribution]
    model_version: str
    detail: dict = field(default_factory=dict)


def _standardize(values: list[float]) -> list[float]:
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    if stdev <= 1e-12:
        return [0.0] * len(values)
    return [(v - mean) / stdev for v in values]


def detect_anomalies(
    samples: list[tuple[uuid.UUID, dict[str, float]]],
    cfg: AnalysisConfig,
) -> tuple[list[AnomalyOutcome], dict]:
    """Fit one Isolation Forest over the whole subject population and score everyone.

    ``samples`` is a list of (subject_id, {feature_id: value}). Order of scoring is
    stable (sorted by subject id), which keeps results reproducible.
    """
    params = {**DEFAULT_PARAMS, **cfg.isolation_forest}
    model_version = str(params.get("model_version", "1.0"))
    ids = [s[0] for s in samples]
    order = sorted(range(len(samples)), key=lambda i: str(ids[i]))

    feature_ids: list[str] = []
    matrix_rows: list[dict[str, float]] = []
    for i in order:
        _, features = samples[i]
        matrix_rows.append(features)
        for key in features:
            if key not in feature_ids:
                feature_ids.append(key)

    outcomes: list[AnomalyOutcome] = []
    if len(samples) < 2:
        # A single subject has no reference population: neutral, reviewable, no flag.
        for sid, features in samples:
            contributions = [
                FeatureContribution(feature_id=k, contribution=1.0 / max(1, len(features)), std_value=0.0, actual_value=v)
                for k, v in features.items()
            ]
            outcomes.append(
                AnomalyOutcome(
                    subject_id=sid,
                    raw_score=0.0,
                    normalized_score=50.0,
                    is_anomaly=False,
                    contributions=contributions,
                    model_version=model_version,
                    detail={"population_size": 1, "note": "No reference population; neutral score."},
                )
            )
        return outcomes, {"model_version": model_version, "population": len(samples)}

    matrix = np.array(
        [[row.get(k, 0.0) for k in feature_ids] for row in matrix_rows],
        dtype=float,
    )
    model = IsolationForest(
        n_estimators=int(params["n_estimators"]),
        contamination=float(params["contamination"]),
        random_state=int(params["random_state"]),
        n_jobs=1,
    )
    model.fit(matrix)
    raw = model.decision_function(matrix)
    flags = model.predict(matrix)  # 1 = inlier, -1 = outlier (deterministic)

    lo, hi = float(raw.min()), float(raw.max())
    span = (hi - lo) or 1.0
    scaled = [float((hi - v) / span) * 100.0 for v in raw]  # 0 normal .. 100 anomalous

    col_values = [matrix[:, i].tolist() for i in range(len(feature_ids))]
    standardized = {feature_id: _standardize(col_values[i]) for i, feature_id in enumerate(feature_ids)}

    for rank, i in enumerate(order):
        sid = ids[i]
        contributions: list[FeatureContribution] = []
        abs_z = {k: abs(v) for k, v in zip(feature_ids, [standardized[k][rank] for k in feature_ids])}
        total = sum(abs_z.values())
        for k in feature_ids:
            share = abs_z[k] / total if total > 1e-12 else 1.0 / max(1, len(feature_ids))
            contributions.append(
                FeatureContribution(
                    feature_id=k,
                    contribution=round(share, 6),
                    std_value=round(standardized[k][rank], 4),
                    actual_value=round(matrix[rank, feature_ids.index(k)], 6),
                )
            )
        contributions.sort(key=lambda c: c.contribution, reverse=True)
        is_anomaly = bool(flags[i] == -1)
        outcomes.append(
            AnomalyOutcome(
                subject_id=sid,
                raw_score=round(float(raw[i]), 6),
                normalized_score=round(scaled[i], 2),
                is_anomaly=is_anomaly,
                contributions=contributions,
                model_version=model_version,
                detail={
                    "population_size": len(samples),
                    "min_raw": round(lo, 6),
                    "max_raw": round(hi, 6),
                    "threshold_raw": round(float(np.quantile(raw, float(params["contamination"]))), 6),
                },
            )
        )
    return outcomes, {"model_version": model_version, "population": len(samples), "params": params}