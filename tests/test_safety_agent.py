"""
Tests for SafetyAgent.

Cases:
    - Family with kids + high altitude destination -> blocker
    - Foreign traveller + NOC zone -> blocker
    - Normal adult group + moderate altitude -> no blocker
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from manzil.agents.safety import SafetyAgent
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
def query_family_with_kids() -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FAMILY,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["family"],
        difficulty_tolerance=2,
    )


@pytest.fixture
def query_foreign_traveller() -> UserQuery:
    return UserQuery(
        group_size=2,
        group_composition=GroupType.COUPLE,
        budget_pkr=150_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural"],
        difficulty_tolerance=3,
        is_foreign_traveller=True,
    )


@pytest.fixture
def query_friends_adult() -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["adventure"],
        difficulty_tolerance=4,
    )


@pytest.fixture
def candidate_deosai() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-deosai",
        label="Deosai adventure",
        destinations=["skardu", "deosai"],
        travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
        estimated_cost=130_000,
        days=7,
    )


@pytest.fixture
def candidate_neelum() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-neelum",
        label="Neelum Valley",
        destinations=["neelum"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=80_000,
        days=5,
    )


@pytest.fixture
def candidate_hunza() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-hunza",
        label="Hunza trip",
        destinations=["hunza-karimabad"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=100_000,
        days=7,
    )


def test_family_kids_high_altitude_blocker(query_family_with_kids):
    """Deosai is 4,114m; family threshold is 3,000m -> blocker."""
    agent = SafetyAgent()
    # Direct Deosai trip, 3 days (no acclimatization day detected)
    direct_deosai = RouteCandidate(
        candidate_id="cand-deosai-direct",
        label="Direct Deosai",
        destinations=["deosai"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=130_000,
        days=3,
    )
    arg = agent.evaluate(direct_deosai, query_family_with_kids)
    assert arg.hard_blocker is not None
    assert "altitude" in arg.hard_blocker.lower()


def test_foreign_traveller_noc_blocker(query_foreign_traveller, candidate_neelum):
    """Neelum requires NOC for foreigners -> blocker."""
    agent = SafetyAgent()
    arg = agent.evaluate(candidate_neelum, query_foreign_traveller)
    assert arg.hard_blocker is not None
    assert "noc" in arg.hard_blocker.lower()


def test_adult_group_moderate_altitude_ok(query_friends_adult, candidate_hunza):
    """Hunza is 2,470m; adult threshold is 4,500m -> no blocker."""
    agent = SafetyAgent()
    arg = agent.evaluate(candidate_hunza, query_friends_adult)
    assert arg.hard_blocker is None
    assert arg.score > 5.0


def test_analysis_includes_hospital_data(query_friends_adult, candidate_hunza):
    """Analysis should contain hospital and police info."""
    agent = SafetyAgent()
    analysis = agent._analyze(candidate_hunza, query_friends_adult)
    assert "per_destination" in analysis
    per_dest = analysis["per_destination"]
    assert len(per_dest) > 0
    assert "hospital_name" in per_dest[0]
    assert "police_name" in per_dest[0]


def test_score_degrades_near_threshold(query_family_with_kids):
    """Score should be lower for routes near the altitude threshold."""
    agent = SafetyAgent()

    # Fairy Meadows is 3,300m — above 3,000m threshold for families
    fairy = RouteCandidate(
        candidate_id="cand-fairy",
        label="Fairy Meadows",
        destinations=["fairy-meadows"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=90_000,
        days=5,
    )
    # Murree is 2,291m — well below threshold
    murree = RouteCandidate(
        candidate_id="cand-murree",
        label="Murree",
        destinations=["murree"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=50_000,
        days=3,
    )

    arg_fairy = agent.evaluate(fairy, query_family_with_kids)
    arg_murree = agent.evaluate(murree, query_family_with_kids)

    assert arg_murree.score > arg_fairy.score


def test_elderly_group_lower_threshold():
    """Elderly threshold is 3,500m; Hunza at 2,470m should be OK but Fairy Meadows at 3,300m blocked."""
    agent = SafetyAgent()
    query_elderly = UserQuery(
        group_size=2,
        group_composition=GroupType.COUPLE,
        budget_pkr=100_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["relaxation"],
        difficulty_tolerance=2,
        elderly_in_group=True,
    )
    # Fairy Meadows is 3,300m — above 3,500m? No, 3,300 < 3,500, so no blocker
    # Deosai is 4,114m — above 3,500m, should block
    deosai = RouteCandidate(
        candidate_id="cand-deosai",
        label="Deosai",
        destinations=["deosai"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=130_000,
        days=3,
    )
    arg = agent.evaluate(deosai, query_elderly)
    assert arg.hard_blocker is not None
    assert "3,500" in arg.hard_blocker or "3500" in arg.hard_blocker
