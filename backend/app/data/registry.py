"""Stable catalog of runtime synthetic scenarios (G2).

Every scenario has a stable reference identifier (its scenario_ref), a category,
a deterministic default seed, and a ground-truth label describing the expected
signal pattern. Re-running a scenario with the same seed and reference date
reproduces the exact same dataset.
"""
from __future__ import annotations

from dataclasses import dataclass

# Stable scenario references (also the values persisted in synthetic_scenarios).
SCENARIO_NORMAL = "SCENARIO_NORMAL_001"
SCENARIO_ISOLATED_ANOMALY = "SCENARIO_ISOLATED_ANOMALY_001"
SCENARIO_TEMPORAL = "SCENARIO_TEMPORAL_001"
SCENARIO_NETWORK = "SCENARIO_NETWORK_001"
SCENARIO_MULTI_SOURCE = "SCENARIO_MULTI_SOURCE_001"
SCENARIO_CORRELATED_ANOMALY = "SCENARIO_CORRELATED_ANOMALY_001"
SCENARIO_FALSE_POSITIVE = "SCENARIO_FALSE_POSITIVE_001"

SCENARIO_TYPES = (
    "NORMAL",
    "ISOLATED_ANOMALY",
    "TEMPORAL",
    "NETWORK",
    "MULTI_SOURCE",
    "CORRELATED_ANOMALY",
    "FALSE_POSITIVE",
)


@dataclass(frozen=True)
class ScenarioSpec:
    ref: str
    scenario_type: str
    label: str
    description: str
    default_seed: int
    ground_truth: str


CATALOG: list[ScenarioSpec] = [
    ScenarioSpec(
        ref=SCENARIO_NORMAL,
        scenario_type="NORMAL",
        label="Routine population baseline",
        description="A routine synthetic population with no concentrated signals for any subject.",
        default_seed=1100,
        ground_truth="Low expected review load; no subject should reach CRITICAL priority.",
    ),
    ScenarioSpec(
        ref=SCENARIO_ISOLATED_ANOMALY,
        scenario_type="ISOLATED_ANOMALY",
        label="Single-source biological deviation",
        description="One subject shows a strong single-source biological marker deviation with no independent corroboration.",
        default_seed=1201,
        ground_truth="Anomaly/rule signal on the target; limited temporal and cross-source corroboration.",
    ),
    ScenarioSpec(
        ref=SCENARIO_TEMPORAL,
        scenario_type="TEMPORAL",
        label="Temporal signal cluster",
        description="One subject shows tightly clustered event activity and a recent whereabouts failure within a short window.",
        default_seed=1302,
        ground_truth="Temporal burst, interval-density and whereabouts signals on the target.",
    ),
    ScenarioSpec(
        ref=SCENARIO_NETWORK,
        scenario_type="NETWORK",
        label="Dense network context",
        description="One subject is densely connected to other moderately active subjects, producing network context.",
        default_seed=1403,
        ground_truth="High network-degree signal; the target should be contextually elevated vs isolated subjects.",
    ),
    ScenarioSpec(
        ref=SCENARIO_MULTI_SOURCE,
        scenario_type="MULTI_SOURCE",
        label="Multi-source corroboration",
        description="Several independent source categories report the same information category about one subject.",
        default_seed=1504,
        ground_truth="Strong corroboration and report-volume signals; cross-source correlation fires.",
    ),
    ScenarioSpec(
        ref=SCENARIO_CORRELATED_ANOMALY,
        scenario_type="CORRELATED_ANOMALY",
        label="Correlated multi-signal concern",
        description="One subject combines a biological deviation, temporal clustering, multi-source reporting and moderate network context.",
        default_seed=1605,
        ground_truth="Multiple independent signal categories contribute to the target's priority.",
    ),
    ScenarioSpec(
        ref=SCENARIO_FALSE_POSITIVE,
        scenario_type="FALSE_POSITIVE",
        label="Strong single non-corroborated signal",
        description="One subject has a strong single-marker anomaly with no corroborating sources; intended to stay reviewable, never terminal.",
        default_seed=1706,
        ground_truth="Rule/anomaly may fire but the subject must remain reviewable (never CRITICAL).",
    ),
]


BY_REF: dict[str, ScenarioSpec] = {spec.ref: spec for spec in CATALOG}


def get_spec(ref: str) -> ScenarioSpec | None:
    return BY_REF.get(ref)


def catalog_summary() -> list[dict]:
    return [
        {
            "ref": spec.ref,
            "scenario_type": spec.scenario_type,
            "label": spec.label,
            "description": spec.description,
            "seed": spec.default_seed,
            "ground_truth": spec.ground_truth,
        }
        for spec in CATALOG
    ]