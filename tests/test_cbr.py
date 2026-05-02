"""Tests for `manzil.recommender.cbr`."""

from __future__ import annotations

from manzil.recommender.cbr import (
    query_similarity,
    route_overlap,
    score_route,
)
from manzil.schemas import (
    CaseBaseEntry,
    GroupType,
    TravelMode,
    UserQuery,
)


def _q(**overrides) -> UserQuery:
    base = dict(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural"],
        difficulty_tolerance=3,
    )
    base.update(overrides)
    return UserQuery(**base)


def _case(
    *, route, rating=4.5, query_overrides=None, persona="test", case_id="c1"
) -> CaseBaseEntry:
    return CaseBaseEntry(
        case_id=case_id,
        query=_q(**(query_overrides or {})),
        chosen_route=route,
        travel_modes=[TravelMode.ROAD] * len(route),
        persona=persona,
        rating=rating,
        feedback_tags=[],
        is_synthetic=True,
    )


# ---------------------------------------------------------------------------
# query_similarity
# ---------------------------------------------------------------------------


def test_identical_query_similarity_is_one():
    q = _q()
    assert query_similarity(q, q) == 1.0


def test_far_query_similarity_is_low():
    # Differ on every attribute — categoricals AND numerics — so we exercise
    # the full weight space, not just the numeric components.
    a = _q(
        budget_pkr=50_000, days=4, travel_month=1,
        style_tags=["adventure"], group_size=1,
        group_composition=GroupType.SOLO,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        difficulty_tolerance=5,
    )
    b = _q(
        budget_pkr=400_000, days=14, travel_month=7,
        style_tags=["family"], group_size=8,
        group_composition=GroupType.FAMILY,
        travel_mode_pref=TravelMode.AIR,
        origin_city="lahore",
        difficulty_tolerance=1,
    )
    assert query_similarity(a, b) < 0.10


def test_month_is_cyclic():
    # Jan vs Dec should be much closer than Jan vs Jul
    a = _q(travel_month=1)
    b = _q(travel_month=12)
    c = _q(travel_month=7)
    assert query_similarity(a, b) > query_similarity(a, c)


# ---------------------------------------------------------------------------
# route_overlap
# ---------------------------------------------------------------------------


def test_route_overlap_identical():
    assert route_overlap(["a", "b"], ["a", "b"]) == 1.0


def test_route_overlap_disjoint():
    assert route_overlap(["a"], ["b"]) == 0.0


def test_route_overlap_partial():
    # {a,b} & {b,c} = {b}; {a,b} | {b,c} = {a,b,c} → 1/3
    val = route_overlap(["a", "b"], ["b", "c"])
    assert abs(val - 1.0 / 3.0) < 1e-9


# ---------------------------------------------------------------------------
# score_route
# ---------------------------------------------------------------------------


def test_score_empty_case_base_returns_zero():
    assert score_route(["a"], _q(), case_base=[]) == 0.0


def test_score_increases_with_high_rated_neighbour():
    cb = [_case(route=["hunza"], rating=5.0)]
    s = score_route(["hunza"], _q(), cb)
    assert s > 0.7


def test_score_drops_when_neighbour_is_route_disjoint():
    cb = [_case(route=["different-place"], rating=5.0)]
    s = score_route(["hunza"], _q(), cb)
    assert s == 0.0


def test_score_is_in_unit_interval():
    cb = [
        _case(route=["a"], rating=5.0, case_id="c1"),
        _case(route=["a"], rating=2.0, case_id="c2"),
        _case(route=["b"], rating=4.0, case_id="c3"),
    ]
    s = score_route(["a"], _q(), cb)
    assert 0.0 <= s <= 1.0
