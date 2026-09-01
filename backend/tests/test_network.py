"""Unit tests for network relevance scoring."""
from __future__ import annotations

from app.analysis.contracts import AnalysisConfig
from app.analysis.network import network_relevance
from tests.support_analytics import AS_OF, make_edge, make_subject, multi_source_subject, network_subject

CFG = AnalysisConfig()


def test_metrics_are_correct():
    out = network_relevance(network_subject(), CFG, AS_OF)
    assert out.degree == 5
    assert out.relationship_diversity == 5
    assert abs(out.weighted_degree - 4.4) < 0.01


def test_isolated_subject_scores_zero():
    out = network_relevance(make_subject(), CFG, AS_OF)
    assert out.degree == 0
    assert out.score == 0.0


def test_connected_high_priority_count_uses_provided_priorities():
    edges = [make_edge("TEAM_MEMBER", 1.0), make_edge("TEAM_MEMBER", 1.0), make_edge("TEAM_MEMBER", 1.0)]
    subj = make_subject(relationships=edges)
    neighbors = [e.other_subject_id for e in edges]
    priorities = {
        neighbors[0]: 95.0,  # CRITICAL -> high priority
        neighbors[1]: 80.0,  # VERY_HIGH -> high priority
        neighbors[2]: 40.0,  # MODERATE -> not counted
    }
    out = network_relevance(subj, CFG, AS_OF, priorities=priorities)
    assert out.connected_priority_count == 2
    assert out.score > network_relevance(subj, CFG, AS_OF).score


def test_score_bounded():
    dense = make_subject(
        relationships=[make_edge("X", 1.0), make_edge("Y", 1.0), make_edge("Z", 1.0)] * 5,
    )
    out = network_relevance(dense, CFG, AS_OF)
    assert 0.0 <= out.score <= 100.0


def test_network_is_relevance_not_guilt_label():
    out = network_relevance(multi_source_subject(), CFG, AS_OF)
    assert out.degree == 0
    assert out.score == 0.0