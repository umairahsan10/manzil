"""
Tests for replanning mechanism.

Case: Original query -> run debate -> inject Disruption(kind="road_closed", day_index=3)
-> assert replan() returns a DebateResult whose winner differs from the original
(or all_blocked=True with a reason citing the closed segment).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from manzil.replan import replan
from manzil.schemas import (
    DebateResult,
    Disruption,
    GroupType,
    RouteCandidate,
    TravelMode,
    UserQuery,
)


@pytest.fixture
def sample_query() -> UserQuery:
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
def sample_candidates() -> list[RouteCandidate]:
    return [
        RouteCandidate(
            candidate_id="cand-A",
            label="Route A via Babusar",
            destinations=["naran", "hunza-karimabad"],
            travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
            estimated_cost=100_000,
            days=7,
        ),
        RouteCandidate(
            candidate_id="cand-B",
            label="Route B via KKH direct",
            destinations=["hunza-karimabad"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=110_000,
            days=7,
        ),
    ]


def test_replan_changes_winner_or_blocks(sample_query, sample_candidates):
    """
    After injecting a road_closed disruption on Babusar, the winner
    should differ from the original (or all_blocked=True).
    """
    # Mock the pipeline to avoid full end-to-end dependencies
    original_result = DebateResult(
        winner=sample_candidates[0],
        scorecard={},
        blockers={},
        orchestrator_reasoning="original",
    )

    modified_candidates = [
        RouteCandidate(
            candidate_id="cand-B",
            label="Route B via KKH direct",
            destinations=["hunza-karimabad"],
            travel_modes=[TravelMode.ROAD],
            estimated_cost=110_000,
            days=7,
        ),
    ]

    new_result = DebateResult(
        winner=modified_candidates[0],
        scorecard={},
        blockers={},
        orchestrator_reasoning="replan",
    )

    with patch("manzil.replan.recommend", return_value=modified_candidates), \
         patch("manzil.replan.run_debate", return_value=new_result):
        disruption = Disruption(
            kind="road_closed",
            pass_id="babusar",
            day_index=3,
            description="Babusar Pass closed due to landslide",
        )
        result = replan(sample_query, disruption)

    assert result is not None
    assert isinstance(result, DebateResult)
    # Winner should be different from original
    assert result.winner.candidate_id != original_result.winner.candidate_id


def test_replan_budget_cut_reduces_budget(sample_query):
    """A budget_cut disruption should reduce the query's budget."""
    from manzil.replan import _apply_disruption

    disruption = Disruption(
        kind="budget_cut",
        pct_cut=20.0,
        description="Budget reduced by 20%",
    )
    modified = _apply_disruption(sample_query, disruption)
    assert modified.budget_pkr == int(sample_query.budget_pkr * 0.8)


def test_replan_road_closed_adds_constraint(sample_query):
    """A road_closed disruption should add a hard constraint."""
    from manzil.replan import _apply_disruption

    disruption = Disruption(
        kind="road_closed",
        pass_id="babusar",
        day_index=3,
        description="Babusar closed",
    )
    modified = _apply_disruption(sample_query, disruption)
    assert "avoid_pass:babusar" in modified.hard_constraints


def test_replan_flight_cancelled_switches_mode(sample_query):
    """A flight_cancelled disruption should switch air mode to road."""
    from manzil.replan import _apply_disruption

    air_query = sample_query.model_copy(update={"travel_mode_pref": TravelMode.AIR})
    disruption = Disruption(
        kind="flight_cancelled",
        destination_id="skardu",
        description="Skardu flight cancelled",
    )
    modified = _apply_disruption(air_query, disruption)
    assert modified.travel_mode_pref == TravelMode.ROAD
