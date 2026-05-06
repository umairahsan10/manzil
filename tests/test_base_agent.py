"""
Verifies the `BaseAgent` contract:
    - `evaluate()` produces a valid `AgentArgument` with all required fields
    - LLM-using agents call `_build_argue_prompt` exactly once per evaluate
    - Stub agents (uses_llm=False) call `_canned_argument` instead of LLM
    - `LLMParseError` from the LLM falls back to confidence=0 with no crash
    - Hard blocker propagates to the returned argument
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from manzil.agents.base import BaseAgent, set_full_llm_mode
from manzil.llm import LLMParseError
from manzil.schemas import (
    AgentArgument,
    GroupType,
    LLMArgumentPayload,
    RouteCandidate,
    TravelMode,
    UserQuery,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def candidate() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-X",
        label="Test candidate",
        destinations=["hunza-karimabad"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=100_000,
        days=7,
    )


# ---------------------------------------------------------------------------
# Fake agent classes for testing
# ---------------------------------------------------------------------------


class _FakeRealAgent(BaseAgent):
    """Uses LLM."""

    name = "FakeRealAgent"
    uses_llm = True

    def _analyze(self, candidate, query):
        return {"echo_dest": candidate.destinations[0], "echo_days": query.days}

    def _check_blocker(self, analysis, candidate, query) -> Optional[str]:
        return None

    def _score(self, analysis, candidate, query) -> float:
        return 7.5

    def _build_argue_prompt(self, analysis, score, candidate, query) -> str:
        return f"prompt-for-{candidate.candidate_id}"


class _FakeStubAgent(BaseAgent):
    """No LLM. Returns canned argument."""

    name = "FakeStubAgent"
    uses_llm = False

    def _analyze(self, candidate, query):
        return {"stub": True}

    def _check_blocker(self, analysis, candidate, query):
        return None

    def _score(self, analysis, candidate, query):
        return 6.0

    def _canned_argument(self, analysis, score, candidate, query) -> LLMArgumentPayload:
        return LLMArgumentPayload(
            reasons=["canned reason"],
            concerns=["canned concern"],
        )


class _FakeBlockingAgent(BaseAgent):
    """No LLM. Always issues a hard blocker."""

    name = "FakeBlockingAgent"
    uses_llm = False

    def _analyze(self, candidate, query):
        return {}

    def _check_blocker(self, analysis, candidate, query):
        return "for testing — always blocks"

    def _score(self, analysis, candidate, query):
        return 0.0

    def _canned_argument(self, analysis, score, candidate, query):
        return LLMArgumentPayload(reasons=[], concerns=["this candidate is unsafe"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_real_agent_calls_llm_once(query, candidate):
    set_full_llm_mode(True)
    payload = LLMArgumentPayload(
        reasons=["good weather"], concerns=["could be hot"]
    )
    with patch("manzil.agents.base.llm.complete_json", return_value=payload) as cj:
        arg = _FakeRealAgent().evaluate(candidate, query)
    assert cj.call_count == 1
    assert isinstance(arg, AgentArgument)
    assert arg.agent_name == "FakeRealAgent"
    assert arg.candidate_id == "cand-X"
    assert arg.score == 7.5
    assert arg.supporting_reasons == ["good weather"]
    assert arg.concerns == ["could be hot"]
    assert arg.hard_blocker is None
    assert arg.confidence == 1.0


def test_stub_agent_does_not_call_llm(query, candidate):
    with patch("manzil.agents.base.llm.complete_json") as cj:
        arg = _FakeStubAgent().evaluate(candidate, query)
    cj.assert_not_called()
    assert arg.agent_name == "FakeStubAgent"
    assert arg.score == 6.0
    assert arg.supporting_reasons == ["canned reason"]
    assert arg.concerns == ["canned concern"]
    assert arg.hard_blocker is None


def test_llm_parse_error_falls_back_to_zero_confidence(query, candidate):
    set_full_llm_mode(True)
    with patch(
        "manzil.agents.base.llm.complete_json",
        side_effect=LLMParseError("bad json"),
    ):
        arg = _FakeRealAgent().evaluate(candidate, query)
    assert arg.score == 7.5  # deterministic score is preserved
    assert arg.supporting_reasons == []
    assert arg.confidence == 0.0
    assert any("argument-generation failed" in c for c in arg.concerns)


def test_blocker_propagates(query, candidate):
    arg = _FakeBlockingAgent().evaluate(candidate, query)
    assert arg.hard_blocker == "for testing — always blocks"
    assert arg.score == 0.0


def test_score_is_clamped(query, candidate):
    class _Overflow(_FakeStubAgent):
        def _score(self, *a, **k):
            return 99.0

    arg = _Overflow().evaluate(candidate, query)
    assert arg.score == 10.0

    class _Underflow(_FakeStubAgent):
        def _score(self, *a, **k):
            return -3.0

    arg = _Underflow().evaluate(candidate, query)
    assert arg.score == 0.0
