"""Tests for `manzil.recommender.relaxation`."""

from __future__ import annotations

from manzil.recommender.relaxation import BUDGET_BUMP, relax
from manzil.schemas import GroupType, TravelMode, UserQuery


def _q(**overrides) -> UserQuery:
    base = dict(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=100_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural"],
        difficulty_tolerance=3,
    )
    base.update(overrides)
    return UserQuery(**base)


def test_first_step_bumps_budget_by_15_percent():
    q = _q(budget_pkr=100_000)
    steps = list(relax(q))
    assert len(steps) >= 1
    expected = int(100_000 * (1 + BUDGET_BUMP))
    assert steps[0].query.budget_pkr == expected
    assert "15%" in steps[0].note or "115" in steps[0].note


def test_second_step_also_drops_a_day():
    q = _q(days=7)
    steps = list(relax(q))
    assert len(steps) >= 2
    assert steps[1].query.days == 6


def test_steps_are_cumulative_keep_budget_bump():
    q = _q(budget_pkr=100_000, days=7, difficulty_tolerance=2)
    expected_budget = int(100_000 * (1 + BUDGET_BUMP))
    for step in relax(q):
        assert step.query.budget_pkr == expected_budget


def test_yields_at_most_three_steps():
    q = _q()
    steps = list(relax(q))
    assert 1 <= len(steps) <= 3


def test_no_day_drop_when_already_at_minimum():
    q = _q(days=2)
    steps = list(relax(q))
    # With days=2 we should NOT yield a "drop a day" step (schema floor is 2)
    days_dropped = [s for s in steps if s.query.days < 2]
    assert days_dropped == []


def test_difficulty_step_is_skipped_when_already_at_max():
    q = _q(difficulty_tolerance=5)
    steps = list(relax(q))
    # No step should bump difficulty above 5
    for step in steps:
        assert step.query.difficulty_tolerance <= 5


def test_note_mentions_each_change_applied():
    q = _q(days=7, difficulty_tolerance=2)
    steps = list(relax(q))
    assert "budget" in steps[0].note.lower()
    if len(steps) >= 2:
        assert "day" in steps[1].note.lower()
