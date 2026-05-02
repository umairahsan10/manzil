"""Tests for `manzil.recommender.diversity`."""

from __future__ import annotations

from manzil.recommender.diversity import (
    AXES,
    compute_axes,
    pick_diverse_three,
)
from manzil.schemas import Destination, GroupType, RouteCandidate, TravelMode, UserQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _dest(*, id, region="Gilgit-Baltistan", altitude_m=2500, difficulty=2) -> Destination:
    return Destination(
        id=id,
        name=id.title(),
        region=region,
        coords=(36.0, 74.0),
        altitude_m=altitude_m,
        terrain_tags=["mountain"],
        activity_tags=["cultural"],
        difficulty=difficulty,
        cost_per_day={"low": 4000, "mid": 8000, "high": 16000},
        season_open=[True] * 12,
        group_suitability=["solo", "couple", "family", "friends", "mixed"],
        accessible=False,
        noc_required_for_foreigners=False,
        description="",
    )


def _cand(
    *,
    id: str,
    cbr: float,
    content: float,
    axes: dict,
    cost: int = 100_000,
    days: int = 7,
    destinations=None,
) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=id,
        label=id,
        destinations=destinations or ["a"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=cost,
        days=days,
        diversity_axes=axes,
        cbr_score=cbr,
        content_score=content,
        rationale="",
    )


# ---------------------------------------------------------------------------
# compute_axes
# ---------------------------------------------------------------------------


def test_compute_axes_returns_all_five_keys():
    dests = {"a": _dest(id="a"), "b": _dest(id="b", region="Punjab")}
    axes = compute_axes(["a", "b"], _q(), dests, estimated_cost=100_000)
    assert set(axes.keys()) == set(AXES)


def test_scope_single_vs_multi_region():
    dests = {
        "a": _dest(id="a", region="Gilgit-Baltistan"),
        "b": _dest(id="b", region="Gilgit-Baltistan"),
    }
    same = compute_axes(["a", "b"], _q(), dests, estimated_cost=100_000)
    assert same["scope"] == "single-region"

    dests["b"] = _dest(id="b", region="Punjab")
    diff = compute_axes(["a", "b"], _q(), dests, estimated_cost=100_000)
    assert diff["scope"] == "multi-region"


def test_risk_buckets_by_altitude():
    dests = {"low": _dest(id="low", altitude_m=2000)}
    assert compute_axes(["low"], _q(), dests, 100_000)["risk"] == "conservative"

    dests = {"mid": _dest(id="mid", altitude_m=3000)}
    assert compute_axes(["mid"], _q(), dests, 100_000)["risk"] == "moderate"

    dests = {"high": _dest(id="high", altitude_m=4000)}
    assert compute_axes(["high"], _q(), dests, 100_000)["risk"] == "ambitious"


def test_budget_posture():
    dests = {"a": _dest(id="a")}
    q = _q(budget_pkr=100_000)
    assert compute_axes(["a"], q, dests, 90_000)["budget_posture"] == "at-budget"
    assert compute_axes(["a"], q, dests, 105_000)["budget_posture"] == "near-budget"
    assert compute_axes(["a"], q, dests, 130_000)["budget_posture"] == "budget-stretch"


# ---------------------------------------------------------------------------
# pick_diverse_three
# ---------------------------------------------------------------------------


def test_returns_three_when_more_supplied():
    cands = [
        _cand(
            id=f"c{i}",
            cbr=0.5 + i * 0.1,
            content=0.5,
            axes={
                "scope": "multi-region" if i % 2 else "single-region",
                "mode_mix": "all-road",
                "pace": "relaxed" if i < 2 else "packed",
                "risk": "moderate",
                "budget_posture": "at-budget",
            },
        )
        for i in range(5)
    ]
    picked = pick_diverse_three(cands)
    assert len(picked) == 3


def test_returns_all_when_three_or_fewer():
    cands = [
        _cand(id="a", cbr=0.6, content=0.5, axes={}),
        _cand(id="b", cbr=0.5, content=0.5, axes={}),
    ]
    picked = pick_diverse_three(cands)
    assert {c.candidate_id for c in picked} == {"a", "b"}


def test_top_pick_is_highest_hybrid():
    cands = [
        _cand(id="best", cbr=0.9, content=0.9, axes={"scope": "single-region"}),
        _cand(id="other", cbr=0.1, content=0.1, axes={"scope": "multi-region"}),
        _cand(id="other2", cbr=0.2, content=0.2, axes={"scope": "single-region"}),
        _cand(id="other3", cbr=0.3, content=0.3, axes={"scope": "single-region"}),
    ]
    picked = pick_diverse_three(cands)
    assert picked[0].candidate_id == "best"


def test_mmr_favors_diverse_over_near_duplicate():
    # Three candidates. Top score: A. Near-duplicate-of-A: B (high score, identical axes).
    # Genuinely different: C (lower score, different axes).
    # MMR with positive lambda should prefer C over B for the second slot.
    cands = [
        _cand(
            id="A",
            cbr=0.9,
            content=0.9,
            axes={
                "scope": "single-region", "mode_mix": "all-road",
                "pace": "relaxed", "risk": "conservative", "budget_posture": "at-budget",
            },
        ),
        _cand(
            id="B",  # near-duplicate
            cbr=0.85,
            content=0.85,
            axes={
                "scope": "single-region", "mode_mix": "all-road",
                "pace": "relaxed", "risk": "conservative", "budget_posture": "at-budget",
            },
        ),
        _cand(
            id="C",  # different on every axis
            cbr=0.6,
            content=0.6,
            axes={
                "scope": "multi-region", "mode_mix": "fly-and-road",
                "pace": "packed", "risk": "ambitious", "budget_posture": "budget-stretch",
            },
        ),
    ]
    picked = pick_diverse_three(cands, lambda_=0.5)
    ids = [c.candidate_id for c in picked]
    assert ids[0] == "A"
    # MMR should place C before B in the second slot because B is an axis-clone of A.
    assert ids.index("C") < ids.index("B")
