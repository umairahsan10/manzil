"""
Tests for multi-key API rotation in manzil.llm.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from manzil import llm
from manzil.tools import cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_llm_state(monkeypatch):
    """Reset module-level key state before each test."""
    monkeypatch.setattr(llm, "_KEYS_INITIALIZED", False)
    monkeypatch.setattr(llm, "_KEY_STATES", [])
    monkeypatch.setattr(llm, "_LAST_KEY_INDEX", -1)


# ---------------------------------------------------------------------------
# Key parsing
# ---------------------------------------------------------------------------


def test_parse_single_key_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSySingle")
    keys = llm._parse_api_keys()
    assert keys == ["AIzaSySingle"]


def test_parse_multiple_keys_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "key1,key2, key3")
    monkeypatch.setenv("GEMINI_API_KEY", "fallback")
    keys = llm._parse_api_keys()
    assert keys == ["key1", "key2", "key3"]


def test_parse_empty_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    keys = llm._parse_api_keys()
    assert keys == []


# ---------------------------------------------------------------------------
# Key selection
# ---------------------------------------------------------------------------


def test_pick_key_round_robin(monkeypatch):
    _reset_llm_state(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEYS", "k1,k2,k3")

    ks1 = llm._pick_available_key()
    ks2 = llm._pick_available_key()
    ks3 = llm._pick_available_key()
    ks4 = llm._pick_available_key()  # should wrap to k1

    assert ks1.key == "k1"
    assert ks2.key == "k2"
    assert ks3.key == "k3"
    assert ks4.key == "k1"


def test_pick_key_skips_unavailable(monkeypatch):
    _reset_llm_state(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEYS", "k1,k2")

    ks1 = llm._pick_available_key()
    ks1.mark_unavailable("test")

    ks2 = llm._pick_available_key()
    assert ks2.key == "k2"

    # k2 is still available, should pick k2 again (k1 is dead)
    ks3 = llm._pick_available_key()
    assert ks3.key == "k2"


def test_pick_key_raises_when_all_exhausted(monkeypatch):
    _reset_llm_state(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEYS", "k1")

    ks = llm._pick_available_key()
    ks.record_call()
    # Burn through 19 more calls to hit daily limit
    for _ in range(19):
        ks.record_call()

    with pytest.raises(llm.LLMError, match="All .* keys exhausted"):
        llm._pick_available_key()


# ---------------------------------------------------------------------------
# Rate limiting per key
# ---------------------------------------------------------------------------


def test_key_state_tracks_calls(monkeypatch):
    state = llm._KeyState("test-key", 0)
    assert state.calls_today() == 0
    state.record_call()
    assert state.calls_today() == 1


def test_key_state_respects_rpm_limit(monkeypatch):
    monkeypatch.setattr(llm, "_RPM_LIMIT", 2)
    state = llm._KeyState("test-key", 0)

    state.record_call()
    state.record_call()
    assert state.can_call() is False  # hit 2/min limit


# ---------------------------------------------------------------------------
# Complete() retry behavior
# ---------------------------------------------------------------------------


def test_complete_retries_on_429(monkeypatch):
    _reset_llm_state(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEYS", "k1,k2")
    llm._ensure_keys()  # Pre-populate so loop knows there are 2 keys

    cache.clear()  # Ensure no cached results interfere

    call_count = 0

    class ResourceExhausted(Exception):
        pass

    def _fake_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate 429 on first key
            raise ResourceExhausted("429 quota exceeded")
        return MagicMock(text="success")

    with patch.object(llm, "_configure_client"):
        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_model.return_value.generate_content = _fake_generate
            result = llm.complete("retry-test-429")

    assert call_count == 2
    assert result == "success"


def test_complete_marks_key_unavailable_on_403(monkeypatch):
    _reset_llm_state(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEYS", "k1,k2")
    llm._ensure_keys()  # Pre-populate

    cache.clear()  # Ensure no cached results interfere

    class PermissionDenied(Exception):
        pass

    def _fake_generate(*args, **kwargs):
        raise PermissionDenied("403 blocked")

    with patch.object(llm, "_configure_client"):
        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_model.return_value.generate_content = _fake_generate
            with pytest.raises(llm.LLMError):
                llm.complete("retry-test-403")

    # k1 should be marked unavailable
    states = llm.get_key_states()
    assert states[0].available is False
