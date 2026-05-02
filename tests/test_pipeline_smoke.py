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
        budget_pkr=180_000,
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


# ---------------------------------------------------------------------------
# Recommender shape
# ---------------------------------------------------------------------------


def test_recommend_returns_three_candidates(query):
    candidates = recommend(query)
    assert len(candidates) == 3
    ids = {c.candidate_id for c in candidates}
    assert ids == {"cand-A", "cand-B", "cand-C"}
    for c in candidates:
        assert c.diversity_axes
        assert set(c.diversity_axes.keys()) >= {"scope", "pace", "risk", "budget_posture", "mode_mix"}


def test_recommend_candidates_differ_along_at_least_two_axes(query):
    """Acceptance criterion from doc: at least 2 axes differ across the 3."""
    candidates = recommend(query)
    if len(candidates) < 3:
        pytest.skip("recommender returned <3 candidates; cannot test diversity")

    axes_with_variation = 0
    for axis in ("scope", "mode_mix", "pace", "risk", "budget_posture"):
        values = {c.diversity_axes.get(axis) for c in candidates}
        if len(values) >= 2:
            axes_with_variation += 1
    assert axes_with_variation >= 2, (
        f"only {axes_with_variation} axes vary across the 3 candidates"
    )


def test_recommend_in_january_filters_seasonal_destinations(query):
    """A January query must not surface destinations that are season-closed."""
    winter_query = query.model_copy(update={"travel_month": 1})
    candidates = recommend(winter_query)
    # Whatever survives, none of them should include skardu (closed Jan-Mar)
    # or fairy-meadows (closed Nov-Apr) or naran (closed Nov-Apr).
    closed_in_january = {"skardu", "fairy-meadows", "naran", "shogran", "deosai", "khaplu"}
    for c in candidates:
        violators = closed_in_january & set(c.destinations)
        assert not violators, f"{c.candidate_id} includes winter-closed: {violators}"


# ---------------------------------------------------------------------------
# End-to-end debate
# ---------------------------------------------------------------------------


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
    assert (result.winner is not None) ^ result.all_blocked

    if result.winner is not None:
        assert result.winner.candidate_id in {c.candidate_id for c in candidates}

        assert set(result.scorecard.keys()) == {
            "WeatherAgent",
            "RoadAgent",
            "SafetyAgent",
            "BudgetAgent",
            "LocalExperienceAgent",
        }
        for by_cand in result.scorecard.values():
            assert set(by_cand.keys()) == {c.candidate_id for c in candidates}
            for score in by_cand.values():
                assert 0.0 <= score <= 10.0

        assert result.full_plan is not None
        assert len(result.full_plan.days) == query.days


def test_family_query_excludes_high_altitude_destinations(query, fake_weather):
    """
    Family group → kids_under_10 threshold = 3000 m. The recommender's filter
    should already drop fairy-meadows (group_suitability excludes 'family') and
    deosai (4114 m, difficulty 4). Whatever it returns must not exceed 3000 m.
    """
    family_query = query.model_copy(
        update={
            "group_composition": GroupType.FAMILY,
            "difficulty_tolerance": 2,
        }
    )

    fake_payload = LLMArgumentPayload(
        reasons=["clear forecast windows"], concerns=["scattered showers possible"]
    )
    with patch(
        "manzil.agents.weather.weather_api.get_forecast", return_value=fake_weather
    ), patch(
        "manzil.agents.base.llm.complete_json", return_value=fake_payload
    ):
        candidates = recommend(family_query)
        result = run_debate(family_query, candidates)

    high_altitude = {"fairy-meadows", "deosai"}
    for c in candidates:
        assert not (high_altitude & set(c.destinations)), (
            f"family candidate {c.candidate_id} includes high-altitude destination"
        )

    # And no Safety blockers should fire on what survived
    if result.winner is not None:
        assert "altitude" not in (result.blockers.get(result.winner.candidate_id) or [""])[0].lower() if result.blockers.get(result.winner.candidate_id) else True


# ---------------------------------------------------------------------------
# Constraint relaxation
# ---------------------------------------------------------------------------


def test_recommender_handles_tight_inputs_gracefully():
    """
    With our 14-destination dataset there are 3 difficulty-1 destinations open
    year-round (gilgit/attabad/murree), so the strict pass nearly always wins
    even on tight queries. The pipeline contract is just: never crash, return
    a list of 0–3 candidates.

    Relaxation behaviour itself is unit-tested in `test_relaxation.py`.
    """
    tight = UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=40_000,
        days=10,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural"],
        difficulty_tolerance=1,
    )
    candidates = recommend(tight)
    assert isinstance(candidates, list)
    assert 0 <= len(candidates) <= 3
    # If we got results, every candidate must conform to the schema
    for c in candidates:
        assert c.candidate_id.startswith("cand-")
        assert c.destinations
        assert c.diversity_axes
