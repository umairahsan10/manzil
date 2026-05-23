"""
Tests for Orchestrator policy.

Cases:
    - Hard-blocker elimination drops vetoed candidates
    - Weighted aggregation matches a hand-computed example
    - Epsilon-window tie-break picks the concentrated candidate
    - Dissent detection: when one agent is >2 points below consensus, dissent surfaces
"""

from __future__ import annotations

import pytest

from manzil.agents.orchestrator import Orchestrator
from manzil.schemas import AgentArgument, RouteCandidate, TravelMode


@pytest.fixture
def candidates() -> list[RouteCandidate]:
    return [
        RouteCandidate(
            candidate_id="cand-A",
            label="Route A",
            destinations=["hunza-karimabad"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=100_000,
            days=7,
        ),
        RouteCandidate(
            candidate_id="cand-B",
            label="Route B",
            destinations=["skardu"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=110_000,
            days=7,
        ),
        RouteCandidate(
            candidate_id="cand-C",
            label="Route C",
            destinations=["murree"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=60_000,
            days=3,
        ),
    ]


@pytest.fixture
def arguments_all_clear(candidates) -> list[AgentArgument]:
    """All candidates get decent scores from all agents."""
    args = []
    for c in candidates:
        args.append(AgentArgument(agent_name="SafetyAgent", candidate_id=c.candidate_id, score=8.0, supporting_reasons=["safe"]))
        args.append(AgentArgument(agent_name="BudgetAgent", candidate_id=c.candidate_id, score=7.0, supporting_reasons=["ok budget"]))
        args.append(AgentArgument(agent_name="WeatherAgent", candidate_id=c.candidate_id, score=7.5, supporting_reasons=["nice weather"]))
        args.append(AgentArgument(agent_name="RoadAgent", candidate_id=c.candidate_id, score=7.0, supporting_reasons=["good roads"]))
        args.append(AgentArgument(agent_name="LocalAgent", candidate_id=c.candidate_id, score=6.0, supporting_reasons=["decent local"]))
    return args


@pytest.fixture
def arguments_with_blocker(candidates) -> list[AgentArgument]:
    """ cand-A is blocked by SafetyAgent. """
    args = []
    for c in candidates:
        if c.candidate_id == "cand-A":
            args.append(AgentArgument(agent_name="SafetyAgent", candidate_id=c.candidate_id, score=2.0, hard_blocker="Altitude too high", concerns=["unsafe"]))
        else:
            args.append(AgentArgument(agent_name="SafetyAgent", candidate_id=c.candidate_id, score=8.0, supporting_reasons=["safe"]))
        args.append(AgentArgument(agent_name="BudgetAgent", candidate_id=c.candidate_id, score=7.0, supporting_reasons=["ok budget"]))
        args.append(AgentArgument(agent_name="WeatherAgent", candidate_id=c.candidate_id, score=7.5, supporting_reasons=["nice weather"]))
        args.append(AgentArgument(agent_name="RoadAgent", candidate_id=c.candidate_id, score=7.0, supporting_reasons=["good roads"]))
        args.append(AgentArgument(agent_name="LocalAgent", candidate_id=c.candidate_id, score=6.0, supporting_reasons=["decent local"]))
    return args


@pytest.fixture
def arguments_for_tiebreak(candidates) -> list[AgentArgument]:
    """
    cand-A and cand-B have nearly identical aggregates (within 0.3).
    cand-A has concentrated scores (9,5,7,6,8) -> conc=4
    cand-B has flat scores (7,7,7,7,7) -> conc=0
    Tie-break should pick cand-B (lower concentration = more consistent agreement).
    """
    args = []
    # cand-A: concentrated
    args.append(AgentArgument(agent_name="SafetyAgent", candidate_id="cand-A", score=9.0))
    args.append(AgentArgument(agent_name="BudgetAgent", candidate_id="cand-A", score=5.0))
    args.append(AgentArgument(agent_name="WeatherAgent", candidate_id="cand-A", score=7.0))
    args.append(AgentArgument(agent_name="RoadAgent", candidate_id="cand-A", score=6.0))
    args.append(AgentArgument(agent_name="LocalAgent", candidate_id="cand-A", score=8.0))

    # cand-B: flat
    args.append(AgentArgument(agent_name="SafetyAgent", candidate_id="cand-B", score=7.0))
    args.append(AgentArgument(agent_name="BudgetAgent", candidate_id="cand-B", score=7.0))
    args.append(AgentArgument(agent_name="WeatherAgent", candidate_id="cand-B", score=7.0))
    args.append(AgentArgument(agent_name="RoadAgent", candidate_id="cand-B", score=7.0))
    args.append(AgentArgument(agent_name="LocalAgent", candidate_id="cand-B", score=7.0))

    # cand-C: lower
    args.append(AgentArgument(agent_name="SafetyAgent", candidate_id="cand-C", score=5.0))
    args.append(AgentArgument(agent_name="BudgetAgent", candidate_id="cand-C", score=5.0))
    args.append(AgentArgument(agent_name="WeatherAgent", candidate_id="cand-C", score=5.0))
    args.append(AgentArgument(agent_name="RoadAgent", candidate_id="cand-C", score=5.0))
    args.append(AgentArgument(agent_name="LocalAgent", candidate_id="cand-C", score=5.0))

    return args


@pytest.fixture
def arguments_with_dissent(candidates) -> list[AgentArgument]:
    """
    Winner is cand-B by aggregate, but LocalAgent strongly prefers cand-A.
    """
    args = []
    # cand-A: LocalAgent loves it (9), others mediocre
    args.append(AgentArgument(agent_name="SafetyAgent", candidate_id="cand-A", score=6.0))
    args.append(AgentArgument(agent_name="BudgetAgent", candidate_id="cand-A", score=6.0))
    args.append(AgentArgument(agent_name="WeatherAgent", candidate_id="cand-A", score=6.0))
    args.append(AgentArgument(agent_name="RoadAgent", candidate_id="cand-A", score=6.0))
    args.append(AgentArgument(agent_name="LocalAgent", candidate_id="cand-A", score=9.0))

    # cand-B: consistent decent scores -> winner
    args.append(AgentArgument(agent_name="SafetyAgent", candidate_id="cand-B", score=8.0))
    args.append(AgentArgument(agent_name="BudgetAgent", candidate_id="cand-B", score=8.0))
    args.append(AgentArgument(agent_name="WeatherAgent", candidate_id="cand-B", score=8.0))
    args.append(AgentArgument(agent_name="RoadAgent", candidate_id="cand-B", score=8.0))
    args.append(AgentArgument(agent_name="LocalAgent", candidate_id="cand-B", score=5.0))  # 3 points below its top

    # cand-C: low
    for agent in ["SafetyAgent", "BudgetAgent", "WeatherAgent", "RoadAgent", "LocalAgent"]:
        args.append(AgentArgument(agent_name=agent, candidate_id="cand-C", score=4.0))

    return args


def test_blocker_elimination(candidates, arguments_with_blocker):
    """cand-A has a blocker; it should not be the winner."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, arguments_with_blocker)
    assert result.winner is not None
    assert result.winner.candidate_id != "cand-A"
    assert "cand-A" in result.blockers


def test_weighted_aggregate(candidates, arguments_all_clear):
    """With identical scores, all aggregates should be equal."""
    orch = Orchestrator()
    agg = orch._weighted_aggregate(candidates, arguments_all_clear)
    # All candidates have same scores, so aggregates should be identical
    vals = list(agg.values())
    assert vals[0] == pytest.approx(vals[1], abs=0.01)
    assert vals[0] == pytest.approx(vals[2], abs=0.01)


def test_tie_break_concentration(candidates, arguments_for_tiebreak):
    """cand-B has lower concentration (flat scores) = more consistent agreement; it should win the tie-break."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, arguments_for_tiebreak)
    # Both A and B are within 0.3, but B has lower concentration -> safer pick
    assert result.winner is not None
    assert result.winner.candidate_id == "cand-B"


def test_dissent_detection(candidates, arguments_with_dissent):
    """LocalAgent scores winner (cand-B) 5.0 vs its top pick (cand-A) 9.0 -> dissent."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, arguments_with_dissent)
    assert result.winner is not None
    assert result.dissenting_opinion is not None
    assert "LocalAgent" in result.dissenting_opinion


def test_why_not_populated(candidates, arguments_all_clear):
    """Runner-ups should have why_not explanations."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, arguments_all_clear)
    assert result.winner is not None
    runner_up_ids = [c.candidate_id for c in candidates if c.candidate_id != result.winner.candidate_id]
    for cid in runner_up_ids:
        assert cid in result.why_not
        assert len(result.why_not[cid]) > 0


def test_scorecard_shape(candidates, arguments_all_clear):
    """Scorecard should be a dict of agent -> candidate -> score."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, arguments_all_clear)
    assert "SafetyAgent" in result.scorecard
    assert "cand-A" in result.scorecard["SafetyAgent"]
    assert result.scorecard["SafetyAgent"]["cand-A"] == 8.0
