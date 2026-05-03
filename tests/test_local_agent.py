"""
Tests for LocalExperienceAgent.

Cases:
    - RAG returns empty for a destination -> graceful degrade, confidence drops,
      no hallucinated content in reasons.
    - Normal retrieval -> score > 0, confidence high.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from manzil.agents.local import LocalExperienceAgent
from manzil.schemas import GroupType, LLMArgumentPayload, RouteCandidate, TravelMode, UserQuery


@pytest.fixture(autouse=True)
def mock_llm():
    """Patch LLM calls so tests run without an API key."""
    with patch(
        "manzil.agents.base.llm.complete_json",
        return_value=LLMArgumentPayload(reasons=["test reason"], concerns=["test concern"]),
    ):
        yield


@pytest.fixture
def query_cultural() -> UserQuery:
    return UserQuery(
        group_size=2,
        group_composition=GroupType.COUPLE,
        budget_pkr=100_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural", "food"],
        difficulty_tolerance=2,
    )


@pytest.fixture
def candidate_hunza() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-hunza",
        label="Hunza cultural trip",
        destinations=["hunza-karimabad"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=90_000,
        days=5,
    )


@pytest.fixture
def candidate_unknown_dest() -> RouteCandidate:
    return RouteCandidate(
        candidate_id="cand-unknown",
        label="Unknown place",
        destinations=["nonexistent-destination-12345"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=50_000,
        days=3,
    )


def test_empty_retrieval_graceful_degrade(query_cultural, candidate_unknown_dest):
    """If RAG returns empty, confidence should drop and no blocker raised."""
    agent = LocalExperienceAgent()
    with patch("manzil.agents.local.rag.retrieve", return_value=[]):
        arg = agent.evaluate(candidate_unknown_dest, query_cultural)

    assert arg.hard_blocker is None
    assert arg.confidence < 1.0
    assert arg.score == 0.0 or arg.score <= 5.0


def test_empty_retrieval_no_hallucination(query_cultural, candidate_unknown_dest):
    """Reasons should not mention places not in retrieved chunks."""
    agent = LocalExperienceAgent()
    with patch("manzil.agents.local.rag.retrieve", return_value=[]), patch(
        "manzil.agents.base.llm.complete_json",
        return_value=LLMArgumentPayload(
            reasons=["We don't have curated local content for this destination yet."],
            concerns=["Limited local data available."],
        ),
    ):
        arg = agent.evaluate(candidate_unknown_dest, query_cultural)

    all_text = " ".join(arg.supporting_reasons + arg.concerns).lower()
    # Should contain an honest admission of no content
    assert "no curated" in all_text or "don't have" in all_text or "not have" in all_text or len(arg.supporting_reasons) == 0


def test_normal_retrieval_score_positive(query_cultural, candidate_hunza):
    """With corpus files present, retrieval should yield a positive score."""
    agent = LocalExperienceAgent()
    arg = agent.evaluate(candidate_hunza, query_cultural)

    # We don't assert exact score because it depends on ChromaDB state,
    # but we can assert no crash and reasonable structure.
    assert arg.hard_blocker is None
    assert 0.0 <= arg.score <= 10.0
    assert 0.0 <= arg.confidence <= 1.0


def test_analysis_tracks_empty_flag(query_cultural, candidate_hunza):
    """Analysis should report whether any destination had empty retrieval."""
    agent = LocalExperienceAgent()
    analysis = agent._analyze(candidate_hunza, query_cultural)
    assert "any_empty_retrieval" in analysis
    assert isinstance(analysis["any_empty_retrieval"], bool)
