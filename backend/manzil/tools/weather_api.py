"""
Open-Meteo wrapper. Free, no API key, generous rate limits.

Returns a `WeatherData` (see `manzil.schemas`). Cached forever-within-session
keyed on (lat, lon, start_date, days). Open-Meteo's free forecast horizon is 16
days — for longer-range planning the agents fall back to a static seasonal
model (built in a later phase).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict

import httpx

from manzil.schemas import WeatherData
from manzil.tools import cache

log = logging.getLogger(__name__)

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_MAX_FORECAST_DAYS = 16


class WeatherError(Exception):
    pass


def _key(lat: float, lon: float, start_date: date, days: int) -> str:
    return cache.stable_key(
        {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "start_date": start_date.isoformat(),
            "days": days,
        }
    )


def get_forecast(
    lat: float,
    lon: float,
    start_date: date,
    days: int,
    *,
    destination_id: str | None = None,
) -> WeatherData:
    """
    Fetch a daily forecast for `days` days starting `start_date`.

    Open-Meteo gives at most 16 forward days; we clamp.
    """
    if days <= 0:
        raise WeatherError("days must be >= 1")
    days = min(days, _MAX_FORECAST_DAYS)
    end_date = start_date + timedelta(days=days - 1)

    key = _key(lat, lon, start_date, days)
    cached = cache.get("weather", key)
    if cached is not None:
        return WeatherData.model_validate(cached)

    if cache.is_demo_mode():
        raise cache.CacheMiss(f"demo mode: no cached weather for key {key}")

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "auto",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(_FORECAST_URL, params=params)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WeatherError(f"Open-Meteo request failed: {exc}") from exc

    daily = data.get("daily") or {}
    wd = WeatherData(
        destination_id=destination_id,
        coords=(lat, lon),
        start_date=start_date.isoformat(),
        days=days,
        daily_temp_max_c=list(daily.get("temperature_2m_max") or []),
        daily_temp_min_c=list(daily.get("temperature_2m_min") or []),
        daily_precip_mm=list(daily.get("precipitation_sum") or []),
        daily_precip_prob=[
            float(p) for p in (daily.get("precipitation_probability_max") or [])
        ],
        summary=_summarize(daily),
    )
    cache.set("weather", key, wd.model_dump())
    return wd


def _summarize(daily: Dict[str, Any]) -> str:
    """Tiny human-readable summary, used for the UI healthcheck row."""
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    pmm = daily.get("precipitation_sum") or []
    if not tmax:
        return ""
    avg_max = sum(tmax) / len(tmax)
    avg_min = sum(tmin) / len(tmin) if tmin else avg_max
    total_precip = sum(pmm) if pmm else 0.0
    return (
        f"avg high {avg_max:.1f}°C, avg low {avg_min:.1f}°C, "
        f"total precip {total_precip:.1f} mm over {len(tmax)} days"
    )


def healthcheck() -> tuple[bool, str]:
    """
    One trivial Open-Meteo round-trip for the Streamlit healthcheck row.
    Uses Karimabad coords and tomorrow as the start.
    """
    try:
        wd = get_forecast(36.3167, 74.6500, date.today() + timedelta(days=1), 3)
        return True, wd.summary or "(no summary)"
    except Exception as exc:  # noqa: BLE001 — UI surface
        return False, f"{type(exc).__name__}: {exc}"


__all__ = ["WeatherError", "get_forecast", "healthcheck"]
