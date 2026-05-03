"""
Tests for BudgetAgent.

Cases:
    - 50% over budget -> blocker
    - Within budget -> high score
    - Slightly over budget (<15%) -> no blocker but lower score
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from manzil.agents.budget import BudgetAgent
from manzil.schemas import GroupType, LLMArgumentPayload, RouteCandidate, TravelMode, UserQuery


@pytest.fixture(autouse=True)
def mock_llm():
    """Patch LLM calls so tests run without an API key."""
    with patch(
        "manzil.agents.base.llm.complete_json",
        return_value=LLMArgumentPayload(reasons=["test reason"], concerns=["test concern"]),
    ):
        yield


@pytest.fixture
def query_mid_budget() -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=100_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["adventure"],
        difficulty_tolerance=3,
    )


@pytest.fixture
def candidate_under_budget() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-cheap",
        label="Budget trip to Murree",
        destinations=["murree"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=60_000,
        days=3,
    )


@pytest.fixture
def candidate_slightly_over() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-mid",
        label="Mid trip to Naran",
        destinations=["naran"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=110_000,
        days=5,
    )


@pytest.fixture
def candidate_way_over() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-expensive",
        label="Luxury trip to Hunza",
        destinations=["hunza-karimabad", "skardu"],
        travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
        estimated_cost=200_000,
        days=7,
    )


def test_within_budget_high_score(candidate_under_budget):
    """A route well under budget should score near 10."""
    agent = BudgetAgent()
    query = UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=300_000,
        days=3,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["adventure"],
        difficulty_tolerance=3,
    )
    arg = agent.evaluate(candidate_under_budget, query)
    assert arg.hard_blocker is None
    assert arg.score >= 9.0


def test_slightly_over_no_blocker(candidate_slightly_over):
    """10% over budget is within the 15% relaxation tolerance."""
    agent = BudgetAgent()
    query = UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=235_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["adventure"],
        difficulty_tolerance=3,
    )
    arg = agent.evaluate(candidate_slightly_over, query)
    assert arg.hard_blocker is None
    assert arg.score < 10.0
    assert arg.score > 5.0


def test_way_over_blocker(query_mid_budget, candidate_way_over):
    """200k vs 100k budget is >15% over -> blocker."""
    agent = BudgetAgent()
    arg = agent.evaluate(candidate_way_over, query_mid_budget)
    assert arg.hard_blocker is not None
    assert "relaxation" in arg.hard_blocker.lower() or "budget" in arg.hard_blocker.lower()


def test_analysis_has_breakdown(query_mid_budget, candidate_under_budget):
    """The analysis should contain a full cost breakdown."""
    agent = BudgetAgent()
    analysis = agent._analyze(candidate_under_budget, query_mid_budget)
    assert "breakdown" in analysis
    bd = analysis["breakdown"]
    assert "transport" in bd
    assert "lodging" in bd
    assert "food" in bd
    assert "activities" in bd
    assert "buffer" in bd


def test_score_monotonic_with_cost(query_mid_budget):
    """Higher cost should yield lower or equal score."""
    agent = BudgetAgent()

    cheap = RouteCandidate(
        candidate_id="cand-cheap",
        label="Cheap",
        destinations=["murree"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=50_000,
        days=3,
    )
    expensive = RouteCandidate(
        candidate_id="cand-expensive",
        label="Expensive",
        destinations=["murree"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=150_000,
        days=3,
    )

    arg_cheap = agent.evaluate(cheap, query_mid_budget)
    arg_exp = agent.evaluate(expensive, query_mid_budget)

    assert arg_cheap.score >= arg_exp.score
