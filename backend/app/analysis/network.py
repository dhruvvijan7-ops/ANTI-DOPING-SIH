"""Network relevance scoring (pipeline stage 10).

Output is network *relevance* (how embedded a subject is and how many connected
entities are already a high priority), never a claim of network guilt.
"""
from __future__ import annotations

import uuid

from app.analysis.contracts import (
    AnalysisConfig,
    NetworkOutcome,
    SubjectData,
)

# A connected subject is "high priority" when its own priority is at least this.
HIGH_PRIORITY_THRESHOLD = 70.0


def network_relevance(
    subject: SubjectData,
    cfg: AnalysisConfig,
    as_of: object,
    priorities: dict[uuid.UUID, float] | None = None,
) -> NetworkOutcome:
    """Compute structural metrics plus count of connected high-priority entities.

    ``priorities`` maps neighbor subject ids to their 0-100 priority from this run.
    """
    edges = subject.relationships
    degree = len(edges)
    weighted_degree = round(sum(e.weight for e in edges), 4)
    diversity = len({e.edge_type for e in edges})
    neighbors = {
        e.other_subject_id
        for e in edges
        if e.other_subject_id is not None
    }
    priorities = priorities or {}
    connected = [
        nid
        for nid in neighbors
        if priorities.get(nid, 0.0) >= HIGH_PRIORITY_THRESHOLD
    ]
    connected_count = len(connected)

    base = min(40.0, degree * 8.0)
    diversity_bonus = min(20.0, max(0.0, diversity - 1) * 10.0)
    weighted_bonus = min(20.0, weighted_degree * 2.0)
    connected_bonus = min(20.0, connected_count * 10.0)
    score = round(
        min(100.0, base + diversity_bonus + weighted_bonus + connected_bonus), 2
    )

    return NetworkOutcome(
        degree=degree,
        weighted_degree=weighted_degree,
        relationship_diversity=diversity,
        connected_priority_count=connected_count,
        score=score,
        detail={
            "neighbors": sorted(str(n) for n in neighbors),
            "connected_high_priority": sorted(str(n) for n in connected),
            "high_priority_threshold": HIGH_PRIORITY_THRESHOLD,
        },
    )