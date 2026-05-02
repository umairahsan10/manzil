"""Tests for `manzil.recommender.filter`."""

from __future__ import annotations

import pytest

from manzil.recommender.filter import filter_destinations
from manzil.schemas import Destination, GroupType, TravelMode, UserQuery


def _dest(
    *,
    id: str = "d1",
    altitude_m: int = 2000,
    difficulty: int = 2,
    season_open=None,
    group_suitability=None,
    accessible: bool = False,
    noc: bool = False,
    activity_tags=None,
) -> Destination:
    return Destination(
        id=id,
        name=id.title(),
        region="Gilgit-Baltistan",
        coords=(36.0, 74.0),
        altitude_m=altitude_m,
        terrain_tags=["mountain"],
        activity_tags=activity_tags or ["cultural"],
        difficulty=difficulty,
        cost_per_day={"low": 4000, "mid": 8000, "high": 16000},
        season_open=season_open or [True] * 12,
        group_suitability=group_suitability or ["solo", "couple", "family", "friends", "mixed"],
        accessible=accessible,
        noc_required_for_foreigners=noc,
        description="",
    )


def _query(
    *,
    travel_month: int = 7,
    difficulty_tolerance: int = 3,
    group_composition: GroupType = GroupType.FRIENDS,
    hard_constraints=None,
) -> UserQuery:
    return UserQuery(
        group_size=4,
        group_composition=group_composition,
        budget_pkr=120_000,
        days=7,
        travel_month=travel_month,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural"],
        difficulty_tolerance=difficulty_tolerance,
        hard_constraints=hard_constraints or [],
    )


def test_keeps_when_all_constraints_pass():
    dests = {"a": _dest(id="a")}
    result = filter_destinations(_query(), dests)
    assert result.feasible_ids == ["a"]
    assert result.dropped == []


def test_drops_when_season_closed():
    closed = [True] * 12
    closed[6] = False  # July (index 6)
    dests = {"a": _dest(id="a", season_open=closed)}
    result = filter_destinations(_query(travel_month=7), dests)
    assert result.feasible == {}
    assert len(result.dropped_for("SEASON_CLOSED")) == 1


def test_drops_when_too_difficult():
    dests = {"a": _dest(id="a", difficulty=5)}
    result = filter_destinations(_query(difficulty_tolerance=3), dests)
    assert result.feasible == {}
    assert len(result.dropped_for("TOO_DIFFICULT")) == 1


def test_drops_when_group_mismatch():
    dests = {"a": _dest(id="a", group_suitability=["couple", "friends"])}
    q = _query(group_composition=GroupType.FAMILY)
    result = filter_destinations(q, dests)
    assert result.feasible == {}
    assert len(result.dropped_for("GROUP_MISMATCH")) == 1


def test_drops_when_wheelchair_required_but_not_accessible():
    dests = {
        "a": _dest(id="a", accessible=False),
        "b": _dest(id="b", accessible=True),
    }
    q = _query(hard_constraints=["wheelchair"])
    result = filter_destinations(q, dests)
    assert result.feasible_ids == ["b"]


def test_drops_when_noc_required_for_foreigner():
    dests = {
        "a": _dest(id="a", noc=True),
        "b": _dest(id="b", noc=False),
    }
    q = _query(hard_constraints=["foreign-passport"])
    result = filter_destinations(q, dests)
    assert result.feasible_ids == ["b"]


def test_multiple_constraints_combine():
    closed = [True] * 12
    closed[0] = False
    dests = {
        "a": _dest(id="a", season_open=closed),                # winter-closed
        "b": _dest(id="b", difficulty=5),                       # too hard
        "c": _dest(id="c"),                                     # OK
    }
    result = filter_destinations(_query(travel_month=1, difficulty_tolerance=3), dests)
    assert result.feasible_ids == ["c"]
    assert len(result.dropped) == 2
