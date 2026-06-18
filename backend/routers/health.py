"""Health and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from manzil.agents.base import is_full_llm_mode
from manzil.tools import cache, weather_api
from manzil import llm

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    """Return system health and configuration status."""
    llm_ok, llm_message = llm.healthcheck()
    weather_ok, weather_message = weather_api.healthcheck()

    keys = []
    for ks in llm.get_key_states():
        keys.append({
            "index": ks.index,
            "available": ks.available,
            "calls_today": ks.calls_today(),
            "last_error": ks.last_error,
        })

    return {
        "status": "healthy" if (llm_ok and weather_ok) else "degraded",
        "cache_enabled": cache.is_enabled(),
        "demo_mode": cache.is_demo_mode(),
        "full_llm_mode": is_full_llm_mode(),
        "cache_dir": str(cache._cache_dir()),
        "llm": {
            "ok": llm_ok,
            "message": llm_message,
            "keys": keys,
        },
        "weather": {
            "ok": weather_ok,
            "message": weather_message,
        },
    }
