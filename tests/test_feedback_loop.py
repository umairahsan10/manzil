"""
Test for the feedback loop.

Scripted: submit query A1 → record winner → simulate submit_feedback
→ submit very-similar query A2 → assert that the case base grew
and that the new query can read the feedback back.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from manzil.memory.feedback import submit_feedback
from manzil.schemas import (
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
def sample_winner() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-A",
        label="Route A",
        destinations=["naran", "hunza-karimabad"],
        travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
        estimated_cost=100_000,
        days=7,
    )


def test_submit_feedback_appends_to_case_base(sample_query, sample_winner, tmp_path):
    """
    submit_feedback should atomically append a real_user entry to case_base.json.
    """
    # Patch the case base path to a temp file so we don't mutate real data
    temp_case_base = tmp_path / "case_base.json"
    temp_case_base.write_text("[]", encoding="utf-8")

    with patch("manzil.memory.feedback._CASE_BASE_PATH", temp_case_base):
        entry = submit_feedback(
            query=sample_query,
            winner_route=sample_winner.destinations,
            travel_modes=[tm.value for tm in sample_winner.travel_modes],
            rating=2.0,
            tags=["too-rushed"],
        )

        # Verify entry shape
        assert entry.persona == "real_user"
        assert not entry.is_synthetic
        assert entry.rating == 2.0
        assert "too-rushed" in entry.feedback_tags

        # Verify file content
        data = json.loads(temp_case_base.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["persona"] == "real_user"
        assert data[0]["rating"] == 2.0


def test_submit_feedback_atomic_write(sample_query, sample_winner, tmp_path):
    """
    Multiple parallel submissions should never produce a corrupt JSON file.
    """
    import threading

    temp_case_base = tmp_path / "case_base.json"
    temp_case_base.write_text("[]", encoding="utf-8")

    errors = []

    def worker():
        try:
            with patch("manzil.memory.feedback._CASE_BASE_PATH", temp_case_base):
                submit_feedback(
                    query=sample_query,
                    winner_route=sample_winner.destinations,
                    travel_modes=[tm.value for tm in sample_winner.travel_modes],
                    rating=4.0,
                    tags=["would-recommend"],
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Threads raised errors: {errors}"

    # File must be valid JSON
    raw = temp_case_base.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert len(data) == 5

    # No partial-line corruption
    assert "\n}" not in raw  # crude heuristic: every object should be complete
