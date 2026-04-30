"""
End-to-end smoke test: form-equivalent UserQuery → recommend → run_debate.

We mock the two real outbound calls (Open-Meteo + Gemini) and assert the
result has the right *shape* — not specific scores. Specific scoring is
covered by per-agent tests in later phases.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from manzil.graph.debate_graph import run_debate
from manzil.recommender.pipeline import recommend
from manzil.schemas import (
    DebateResult,
    GroupType,
    LLMArgumentPayload,
    TravelMode,
    UserQuery,
    WeatherData,
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
        origin_city="karachi",
        style_tags=["cultural", "photography"],
        difficulty_tolerance=3,
    )


@pytest.fixture
def fake_weather() -> WeatherData:
    return WeatherData(
        coords=(36.3167, 74.6500),
        start_date=date.today().isoformat(),
        days=3,
        daily_temp_max_c=[24.0, 23.0, 22.0],
        daily_temp_min_c=[12.0, 11.0, 10.0],
        daily_precip_mm=[0.0, 1.5, 0.0],
        daily_precip_prob=[10.0, 30.0, 5.0],
        summary="mild and mostly dry",
    )


def test_recommend_returns_three_diverse_candidates(query):
    candidates = recommend(query)
    assert len(candidates) == 3
    ids = {c.candidate_id for c in candidates}
    assert ids == {"cand-A", "cand-B", "cand-C"}
    # Each has at least one diversity axis tagged
    for c in candidates:
        assert c.diversity_axes
        assert "scope" in c.diversity_axes


def test_full_debate_smoke(query, fake_weather):
    fake_payload = LLMArgumentPayload(
        reasons=["clear forecast windows"],
        concerns=["scattered showers possible"],
    )
    with patch(
        "manzil.agents.weather.weather_api.get_forecast",
        return_value=fake_weather,
    ), patch(
        "manzil.agents.base.llm.complete_json",
        return_value=fake_payload,
    ):
        candidates = recommend(query)
        result = run_debate(query, candidates)

    assert isinstance(result, DebateResult)
    # Either a winner is picked OR all_blocked is True; never both
    assert (result.winner is not None) ^ result.all_blocked

    # If we got a winner, it must be one of the recommended candidates
    if result.winner is not None:
        assert result.winner.candidate_id in {c.candidate_id for c in candidates}

        # Scorecard is 5 agents × 3 candidates = 15 cells, all populated
        assert set(result.scorecard.keys()) == {
            "WeatherAgent",
            "RoadAgent",
            "SafetyAgent",
            "BudgetAgent",
            "LocalExperienceAgent",
        }
        for agent_name, by_cand in result.scorecard.items():
            assert set(by_cand.keys()) == {c.candidate_id for c in candidates}
            for score in by_cand.values():
                assert 0.0 <= score <= 10.0

        # Day-by-day plan exists and has the right number of days
        assert result.full_plan is not None
        assert len(result.full_plan.days) == query.days


def test_debate_with_kids_blocks_high_altitude(query, fake_weather):
    """
    Family group — SafetyAgent threshold drops to 3000 m, so the ambitious
    candidate (which includes Fairy Meadows at 3300 m) must be blocked.
    """
    family_query = query.model_copy(update={"group_composition": GroupType.FAMILY})

    fake_payload = LLMArgumentPayload(
        reasons=["clear forecast windows"],
        concerns=["scattered showers possible"],
    )
    with patch(
        "manzil.agents.weather.weather_api.get_forecast",
        return_value=fake_weather,
    ), patch(
        "manzil.agents.base.llm.complete_json",
        return_value=fake_payload,
    ):
        candidates = recommend(family_query)
        result = run_debate(family_query, candidates)

    # Cand-C (ambitious, includes Fairy Meadows 3300 m) must be in blockers
    assert "cand-C" in result.blockers
    assert any("Altitude" in r for r in result.blockers["cand-C"])
    # And the winner must NOT be cand-C
    if result.winner is not None:
        assert result.winner.candidate_id != "cand-C"
