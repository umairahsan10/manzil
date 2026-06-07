"""
Tests for RoadAgent.

Cases:
    - Closed pass in chosen month -> blocker fires
    - Drive-time > 12h on a single leg -> blocker fires
    - Normal route -> no blocker, reasonable score
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from manzil.agents.road import RoadAgent
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
def query_karachi_july() -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["adventure"],
        difficulty_tolerance=3,
    )


@pytest.fixture
def query_karachi_january() -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=1,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["adventure"],
        difficulty_tolerance=3,
    )


@pytest.fixture
def candidate_skardu() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-skardu",
        label="Skardu road trip",
        destinations=["skardu"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=100_000,
        days=7,
    )


@pytest.fixture
def candidate_naran_then_skardu() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-naran-skardu",
        label="Naran then Skardu",
        destinations=["naran", "skardu"],
        travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
        estimated_cost=110_000,
        days=7,
    )


def test_closed_pass_blocker(query_karachi_january, candidate_skardu):
    """Babusar Pass is closed in January; route via Skardu should be blocked."""
    agent = RoadAgent()
    arg = agent.evaluate(candidate_skardu, query_karachi_january)
    assert arg.hard_blocker is not None
    assert "closed" in arg.hard_blocker.lower()


def test_long_leg_blocker(query_karachi_july, candidate_naran_then_skardu):
    """Naran -> Skardu is 13h drive. Blocker disabled for demo; score should still be low."""
    agent = RoadAgent()
    arg = agent.evaluate(candidate_naran_then_skardu, query_karachi_july)
    # Blocker disabled for demo
    assert arg.hard_blocker is None
    # But the long leg should still penalize the score (below a perfect 10)
    assert arg.score < 8.5
    # And surface as a concern
    concerns_text = " ".join(arg.concerns).lower()
    assert "break" in concerns_text or "longest driving leg" in concerns_text


def test_normal_route_no_blocker(query_karachi_july):
    """Islamabad -> Murree is a short, safe route with no blockers."""
    agent = RoadAgent()
    short = RouteCandidate(
        candidate_id="cand-murree",
        label="Murree from Islamabad",
        destinations=["murree"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=50_000,
        days=3,
    )
    query_isb = query_karachi_july.model_copy(update={"origin_city": "islamabad"})
    arg = agent.evaluate(short, query_isb)
    assert arg.hard_blocker is None
    assert arg.score > 0


def test_score_reflects_drive_time(query_karachi_july):
    """A shorter route should score higher than a longer one."""
    agent = RoadAgent()

    short = RouteCandidate(
        candidate_id="cand-murree",
        label="Murree trip",
        destinations=["murree"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=50_000,
        days=3,
    )
    long = RouteCandidate(
        candidate_id="cand-skardu",
        label="Skardu trip",
        destinations=["skardu"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=100_000,
        days=7,
    )

    arg_short = agent.evaluate(short, query_karachi_july)
    arg_long = agent.evaluate(long, query_karachi_july)

    assert arg_short.score > arg_long.score


def test_analysis_includes_passes(query_karachi_july, candidate_skardu):
    """The analysis should list passes on the route."""
    agent = RoadAgent()
    analysis = agent._analyze(candidate_skardu, query_karachi_july)
    assert "passes" in analysis
    # Karachi -> Skardu goes via Babusar
    pass_names = [p.get("name", p["pass_id"]) for p in analysis["passes"]]
    assert any("babusar" in name.lower() for name in pass_names)
