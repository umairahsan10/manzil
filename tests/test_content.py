"""Tests for `manzil.recommender.content`."""

from __future__ import annotations

from manzil.recommender.content import score_route
from manzil.schemas import Destination, GroupType, TravelMode, UserQuery


def _dest(*, id: str, activity_tags, difficulty=2) -> Destination:
    return Destination(
        id=id,
        name=id.title(),
        region="Gilgit-Baltistan",
        coords=(36.0, 74.0),
        altitude_m=2000,
        terrain_tags=["mountain"],
        activity_tags=activity_tags,
        difficulty=difficulty,
        cost_per_day={"low": 4000, "mid": 8000, "high": 16000},
        season_open=[True] * 12,
        group_suitability=["solo", "couple", "family", "friends", "mixed"],
        accessible=False,
        noc_required_for_foreigners=False,
        description="",
    )


def _q(*, style_tags, difficulty=3) -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=style_tags,
        difficulty_tolerance=difficulty,
    )


def test_perfect_overlap_scores_high():
    dests = {"a": _dest(id="a", activity_tags=["cultural", "photography"], difficulty=3)}
    score = score_route(
        ["a"], _q(style_tags=["cultural", "photography"], difficulty=3), dests
    )
    assert score > 0.85


def test_disjoint_styles_scores_low():
    dests = {"a": _dest(id="a", activity_tags=["adventure", "trekking"], difficulty=4)}
    score = score_route(["a"], _q(style_tags=["family", "shopping"], difficulty=1), dests)
    assert score < 0.4


def test_difficulty_match_contributes():
    # Same tag overlap, different difficulty match
    dests_match = {"a": _dest(id="a", activity_tags=["cultural"], difficulty=3)}
    dests_off = {"a": _dest(id="a", activity_tags=["cultural"], difficulty=5)}
    s_match = score_route(["a"], _q(style_tags=["cultural"], difficulty=3), dests_match)
    s_off = score_route(["a"], _q(style_tags=["cultural"], difficulty=3), dests_off)
    assert s_match > s_off


def test_empty_route_scores_zero():
    assert score_route([], _q(style_tags=["cultural"], difficulty=3), {}) == 0.0


def test_score_is_in_unit_interval():
    dests = {"a": _dest(id="a", activity_tags=["cultural", "history"], difficulty=2)}
    s = score_route(["a"], _q(style_tags=["cultural"], difficulty=3), dests)
    assert 0.0 <= s <= 1.0
