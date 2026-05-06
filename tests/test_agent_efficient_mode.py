"""
Tests for efficient mode (templated arguments, zero LLM calls per agent).
"""

from __future__ import annotations

import pytest

from manzil.agents.base import set_full_llm_mode
from manzil.agents.budget import BudgetAgent
from manzil.agents.local import LocalExperienceAgent
from manzil.agents.road import RoadAgent
from manzil.agents.safety import SafetyAgent
from manzil.agents.weather import WeatherAgent
from manzil.schemas import (
    AgentArgument,
    GroupType,
    RouteCandidate,
    TravelMode,
    UserQuery,
)


@pytest.fixture
def query() -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="islamabad",
        style_tags=["cultural", "photography"],
        difficulty_tolerance=3,
    )


@pytest.fixture
def candidate() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-test",
        label="Test Route",
        destinations=["hunza-karimabad", "skardu"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=100_000,
        days=7,
    )


# ---------------------------------------------------------------------------
# Efficient mode produces valid arguments
# ---------------------------------------------------------------------------

AGENTS = [
    (RoadAgent, "RoadAgent"),
    (WeatherAgent, "WeatherAgent"),
    (SafetyAgent, "SafetyAgent"),
    (BudgetAgent, "BudgetAgent"),
    (LocalExperienceAgent, "LocalAgent"),
]


@pytest.mark.parametrize("agent_cls,expected_name", AGENTS)
def test_agent_efficient_mode(agent_cls, expected_name, query, candidate):
    set_full_llm_mode(False)
    agent = agent_cls()
    arg = agent.evaluate(candidate, query)
    assert isinstance(arg, AgentArgument)
    assert arg.agent_name == expected_name
    assert 0.0 <= arg.score <= 10.0
    assert len(arg.supporting_reasons) > 0


# ---------------------------------------------------------------------------
# Arguments are grounded in analysis (no hallucination)
# ---------------------------------------------------------------------------


def test_road_arguments_grounded_in_data(query, candidate):
    set_full_llm_mode(False)
    agent = RoadAgent()
    arg = agent.evaluate(candidate, query)
    analysis = agent._analyze(candidate, query)

    all_text = " ".join(arg.supporting_reasons + arg.concerns).lower()
    avg_drive = analysis["avg_drive_per_day_hours"]
    assert str(avg_drive) in all_text or str(int(avg_drive)) in all_text


def test_budget_arguments_mention_cost(query, candidate):
    set_full_llm_mode(False)
    agent = BudgetAgent()
    arg = agent.evaluate(candidate, query)

    all_text = " ".join(arg.supporting_reasons + arg.concerns).lower()
    assert "pkr" in all_text or "budget" in all_text


# ---------------------------------------------------------------------------
# Blockers still work in efficient mode
# ---------------------------------------------------------------------------


def test_safety_blocker_still_fires_efficient_mode():
    set_full_llm_mode(False)
    query = UserQuery(
        group_size=2,
        group_composition=GroupType.FRIENDS,
        budget_pkr=200_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="islamabad",
        style_tags=["adventure"],
        difficulty_tolerance=3,
        is_foreign_traveller=True,
    )
    candidate = RouteCandidate(
        candidate_id="cand-noc",
        label="NOC Route",
        destinations=["khunjerab"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=150_000,
        days=5,
    )
    agent = SafetyAgent()
    arg = agent.evaluate(candidate, query)
    assert arg.hard_blocker is not None
    assert "noc" in arg.hard_blocker.lower()
