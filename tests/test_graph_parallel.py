"""
Tests for graph parallelism.

Case: Time the graph with 5 agents that each sleep(0.5).
Total runtime < 1 second proves parallelism.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from manzil.agents.base import BaseAgent
from manzil.graph.debate_graph import run_debate
from manzil.schemas import (
    AgentArgument,
    GroupType,
    LLMArgumentPayload,
    RouteCandidate,
    TravelMode,
    UserQuery,
)


@pytest.fixture(autouse=True)
def mock_llm_and_embeddings():
    """Patch LLM and embedding calls so graph tests run without an API key."""
    with patch(
        "manzil.agents.base.llm.complete_json",
        return_value=LLMArgumentPayload(reasons=["test reason"], concerns=["test concern"]),
    ), patch(
        "manzil.llm.complete",
        return_value="Synthesis paragraph for testing.",
    ), patch(
        "manzil.tools.rag._embed_texts",
        return_value=[[0.1] * 768],
    ):
        yield


class _SlowAgent(BaseAgent):
    """Agent that sleeps for a fixed duration to test parallelism."""

    name = "SlowAgent"
    uses_llm = False
    _sleep_seconds = 0.5

    def __init__(self, agent_name: str):
        super().__init__()
        self.name = agent_name

    def _analyze(self, candidate, query):
        return {"sleep": self._sleep_seconds}

    def _check_blocker(self, analysis, candidate, query):
        return None

    def _score(self, analysis, candidate, query):
        return 5.0

    def _canned_argument(self, analysis, score, candidate, query):
        import time
        time.sleep(self._sleep_seconds)
        return LLMArgumentPayload(reasons=["ok"], concerns=[])


def test_parallel_runtime():
    """
    If the graph runs 5 agents in parallel, each sleeping 0.5s,
    total time should be < 1s (not 2.5s).
    """
    # We patch the agent constructors in the graph to return slow agents
    query = UserQuery(
        group_size=2,
        group_composition=GroupType.COUPLE,
        budget_pkr=100_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural"],
        difficulty_tolerance=2,
    )
    candidates = [
        RouteCandidate(
            candidate_id="cand-A",
            label="Test route",
            destinations=["hunza-karimabad"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=90_000,
            days=5,
        ),
    ]

    # Patch the graph's agent nodes to use slow agents
    # We need to patch the _make_agent_node factory or the agent classes
    # A simpler approach: patch the evaluate methods on the real agents
    def make_slow_evaluate(sleep_time):
        orig_evaluate = BaseAgent.evaluate
        def slow_evaluate(self, candidate, query):
            import time
            time.sleep(sleep_time)
            return AgentArgument(
                agent_name=self.name,
                candidate_id=candidate.candidate_id,
                score=5.0,
                supporting_reasons=["slow test"],
                concerns=[],
            )
        return slow_evaluate

    with patch.multiple(
        "manzil.agents.weather.WeatherAgent",
        evaluate=make_slow_evaluate(0.5),
    ), patch.multiple(
        "manzil.agents.road.RoadAgent",
        evaluate=make_slow_evaluate(0.5),
    ), patch.multiple(
        "manzil.agents.safety.SafetyAgent",
        evaluate=make_slow_evaluate(0.5),
    ), patch.multiple(
        "manzil.agents.budget.BudgetAgent",
        evaluate=make_slow_evaluate(0.5),
    ), patch.multiple(
        "manzil.agents.local.LocalExperienceAgent",
        evaluate=make_slow_evaluate(0.5),
    ):
        start = time.time()
        result = run_debate(query, candidates)
        elapsed = time.time() - start

    # Parallel: should be < 1.0s (allow some overhead)
    # Sequential: would be ~2.5s
    assert elapsed < 1.5, f"Elapsed {elapsed:.2f}s suggests sequential execution"
    assert result is not None


def test_graph_returns_debate_result():
    """The graph should return a DebateResult with a winner."""
    query = UserQuery(
        group_size=2,
        group_composition=GroupType.COUPLE,
        budget_pkr=300_000,
        days=3,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="islamabad",
        style_tags=["cultural"],
        difficulty_tolerance=2,
    )
    candidates = [
        RouteCandidate(
            candidate_id="cand-A",
            label="Test route to Murree",
            destinations=["murree"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=80_000,
            days=3,
        ),
    ]

    result = run_debate(query, candidates)
    assert result is not None
    assert result.winner is not None
    assert result.scorecard is not None
    assert len(result.scorecard) > 0


def test_run_debate_stream_yields_events():
    """run_debate_stream yields 5 agent_done events + 1 orchestrator_done."""
    query = UserQuery(
        group_size=2,
        group_composition=GroupType.COUPLE,
        budget_pkr=300_000,
        days=3,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="islamabad",
        style_tags=["cultural"],
        difficulty_tolerance=2,
    )
    candidates = [
        RouteCandidate(
            candidate_id="cand-A",
            label="Test route to Murree",
            destinations=["murree"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=80_000,
            days=3,
        ),
    ]

    from manzil.graph.debate_graph import run_debate_stream

    agent_count = 0
    orch_done = False
    result = None

    for event in run_debate_stream(query, candidates, use_full_llm=False):
        if event["type"] == "agent_done":
            agent_count += 1
            assert "agent" in event
            assert "arguments" in event
        elif event["type"] == "orchestrator_done":
            orch_done = True
            result = event["result"]

    assert agent_count == 5, f"Expected 5 agent events, got {agent_count}"
    assert orch_done, "Missing orchestrator_done event"
    assert result is not None
    assert result.winner is not None
