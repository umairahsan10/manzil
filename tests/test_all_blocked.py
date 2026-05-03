"""
Tests for all-blocked failure mode.

Case: A query where every candidate is safety-blocked ->
      DebateResult(winner=None, all_blocked=True, blockers=...)
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
            destinations=["deosai"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=130_000,
            days=7,
        ),
        RouteCandidate(
            candidate_id="cand-B",
            label="Route B",
            destinations=["fairy-meadows", "deosai"],
            travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
            estimated_cost=150_000,
            days=7,
        ),
        RouteCandidate(
            candidate_id="cand-C",
            label="Route C",
            destinations=["skardu", "deosai"],
            travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
            estimated_cost=140_000,
            days=7,
        ),
    ]


@pytest.fixture
def all_blocked_arguments(candidates) -> list[AgentArgument]:
    """SafetyAgent blocks every candidate (altitude too high for family with kids)."""
    args = []
    for c in candidates:
        args.append(AgentArgument(
            agent_name="SafetyAgent",
            candidate_id=c.candidate_id,
            score=1.0,
            hard_blocker="Altitude exceeds threshold without acclimatization",
            concerns=["too high"],
        ))
        args.append(AgentArgument(agent_name="BudgetAgent", candidate_id=c.candidate_id, score=5.0))
        args.append(AgentArgument(agent_name="WeatherAgent", candidate_id=c.candidate_id, score=6.0))
        args.append(AgentArgument(agent_name="RoadAgent", candidate_id=c.candidate_id, score=5.0))
        args.append(AgentArgument(agent_name="LocalAgent", candidate_id=c.candidate_id, score=5.0))
    return args


def test_all_blocked_result(candidates, all_blocked_arguments):
    """When all candidates are blocked, winner should be None."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, all_blocked_arguments)
    assert result.all_blocked is True
    assert result.winner is None
    assert result.full_plan is None


def test_all_blocked_blockers_listed(candidates, all_blocked_arguments):
    """All candidates should appear in the blockers dict."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, all_blocked_arguments)
    for c in candidates:
        assert c.candidate_id in result.blockers
        assert len(result.blockers[c.candidate_id]) > 0


def test_all_blocked_reasoning_provided(candidates, all_blocked_arguments):
    """Orchestrator should provide explanatory reasoning."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, all_blocked_arguments)
    assert len(result.orchestrator_reasoning) > 0
    assert "No candidate survived" in result.orchestrator_reasoning or "blocked" in result.orchestrator_reasoning.lower()


def test_all_blocked_scorecard_still_present(candidates, all_blocked_arguments):
    """Even when all blocked, scorecard should be populated for transparency."""
    orch = Orchestrator()
    result = orch.synthesize(candidates, all_blocked_arguments)
    assert len(result.scorecard) > 0
    assert "SafetyAgent" in result.scorecard
