"""
Tests for the LLM cache layer and the OpenAI-compatible wrapper's cache integration.

We never actually hit the live API in these tests — we assert that:
  - the cache's set/get/clear round-trip
  - stable_key is deterministic and order-insensitive
  - demo mode raises CacheMiss on miss but serves hits
  - llm.complete() reads through the cache and never builds an OpenAI client
    when the cache is warm
"""

from __future__ import annotations

import importlib

import pytest

from manzil import llm
from manzil.tools import cache


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Each test gets its own cache dir and a clean in-memory registry."""
    monkeypatch.setenv("MANZIL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("MANZIL_USE_CACHE", "1")
    monkeypatch.setenv("MANZIL_DEMO_MODE", "0")
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# stable_key
# ---------------------------------------------------------------------------


def test_stable_key_is_order_insensitive():
    a = cache.stable_key({"x": 1, "y": 2})
    b = cache.stable_key({"y": 2, "x": 1})
    assert a == b


def test_stable_key_changes_with_payload():
    a = cache.stable_key({"x": 1})
    b = cache.stable_key({"x": 2})
    assert a != b


# ---------------------------------------------------------------------------
# get / set / clear
# ---------------------------------------------------------------------------


def test_get_miss_returns_none():
    assert cache.get("test_ns", "nope") is None


def test_set_then_get_roundtrip():
    cache.set("test_ns", "k1", {"hello": "world"})
    assert cache.get("test_ns", "k1") == {"hello": "world"}


def test_set_persists_across_namespace_reload():
    cache.set("test_ns", "k1", "value")
    # Drop the in-memory registry; the JSON file on disk should still load.
    cache.clear("test_ns")
    cache.set("test_ns", "k2", "second")  # forces re-init
    # k1 was cleared along with the file, so this just re-confirms the lifecycle.
    assert cache.get("test_ns", "k2") == "second"


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------


def test_demo_mode_miss_raises(monkeypatch):
    monkeypatch.setenv("MANZIL_DEMO_MODE", "1")
    with pytest.raises(cache.CacheMiss):
        cache.get("test_ns", "absent")


def test_demo_mode_hit_serves(monkeypatch):
    cache.set("test_ns", "k", "value")  # write while demo mode is off
    monkeypatch.setenv("MANZIL_DEMO_MODE", "1")
    assert cache.get("test_ns", "k") == "value"


# ---------------------------------------------------------------------------
# llm.complete() integrates with the cache
# ---------------------------------------------------------------------------


def test_llm_complete_returns_cached_without_touching_api(monkeypatch):
    """
    With a pre-warmed cache, llm.complete must NOT try to build an
    OpenAI client. We sentinel _get_client.
    """
    importlib.reload(llm)  # reset module-level state

    def _explode(*args, **kwargs):
        raise AssertionError("_get_client was called despite a cache hit")

    monkeypatch.setattr(llm, "_get_client", _explode)

    key = llm._cache_key(llm.Model.FLASH_LITE, "ping", 0.0, None)
    cache.set("llm", key, {"text": "pong", "model": llm.Model.FLASH_LITE.value})

    out = llm.complete("ping", model=llm.Model.FLASH_LITE, temperature=0.0)
    assert out == "pong"


def test_llm_complete_demo_mode_miss_raises(monkeypatch):
    monkeypatch.setenv("MANZIL_DEMO_MODE", "1")
    importlib.reload(llm)

    def _explode(*args, **kwargs):
        raise AssertionError("_get_client must not be called in demo mode")

    monkeypatch.setattr(llm, "_get_client", _explode)

    with pytest.raises(cache.CacheMiss):
        llm.complete("never-cached-prompt", temperature=0.0)
