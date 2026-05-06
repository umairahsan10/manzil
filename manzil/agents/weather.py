"""
WeatherAgent — the first real agent in the system.

Pulls a forecast for each destination on the candidate route via Open-Meteo
(`manzil.tools.weather_api`), aggregates per-destination weather features
into a deterministic score, then asks Gemini to phrase the agent's
position in 2–3 short reasons + 1–3 short concerns.

Phase-1 caveat: Open-Meteo's free forecast horizon is 16 days. If the
user's `travel_month` is further out, we use **today + 1 day** as a
near-term proxy and surface that fact in `analysis.note`. A proper
seasonal model lands in Phase 3.
"""

from __future__ import annotations

import json
import statistics
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from manzil.agents.base import BaseAgent
from manzil.data_loader import load_destinations
from manzil.schemas import LLMArgumentPayload, RouteCandidate, UserQuery
from manzil.tools import cache, weather_api

_SEASONAL_WEATHER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "seasonal_weather.json"


def _load_seasonal_weather() -> Dict[str, Any]:
    if not _SEASONAL_WEATHER_PATH.exists():
        return {}
    with _SEASONAL_WEATHER_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _seasonal_data_for_destination(dest_id: str, month: int) -> Optional[Dict[str, Any]]:
    """Return seasonal weather dict for a destination and month (1-12)."""
    data = _load_seasonal_weather()
    dest_data = data.get("destinations", {}).get(dest_id)
    if dest_data is None:
        return None
    idx = month - 1
    return {
        "avg_high_c": dest_data["avg_high_c"][idx],
        "avg_low_c": dest_data["avg_low_c"][idx],
        "avg_precip_mm": dest_data["avg_precip_mm"][idx],
    }

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class WeatherAgent(BaseAgent):
    name = "WeatherAgent"
    uses_llm = True

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        destinations_by_id = load_destinations()
        use_seasonal = self._should_use_seasonal(query)
        start = self._forecast_start_for_query(query, use_seasonal)
        days_per_dest = max(1, candidate.days // max(1, len(candidate.destinations)))
        days_per_dest = min(days_per_dest, 7)  # cap per-destination forecast

        per_dest: Dict[str, Dict[str, Any]] = {}
        for dest_id in candidate.destinations:
            dest = destinations_by_id.get(dest_id)
            if dest is None:
                per_dest[dest_id] = {"error": f"unknown destination id {dest_id!r}"}
                continue

            if use_seasonal:
                # Use seasonal model
                seasonal = _seasonal_data_for_destination(dest_id, query.travel_month)
                if seasonal is None:
                    per_dest[dest_id] = {
                        "name": dest.name,
                        "altitude_m": dest.altitude_m,
                        "error": "no seasonal data available",
                    }
                    continue

                avg_high = seasonal["avg_high_c"]
                avg_low = seasonal["avg_low_c"]
                total_precip = seasonal["avg_precip_mm"] * days_per_dest
                # Estimate wet days from monthly precip
                wet_days = 2 if seasonal["avg_precip_mm"] > 50 else (1 if seasonal["avg_precip_mm"] > 20 else 0)
                peak_precip_prob = 70 if seasonal["avg_precip_mm"] > 80 else (40 if seasonal["avg_precip_mm"] > 30 else 10)

                per_dest[dest_id] = {
                    "name": dest.name,
                    "altitude_m": dest.altitude_m,
                    "avg_high_c": _r1(avg_high),
                    "avg_low_c": _r1(avg_low),
                    "total_precip_mm": _r1(total_precip),
                    "peak_precip_prob_pct": _r0(peak_precip_prob),
                    "wet_days_count": wet_days,
                    "summary": (
                        f"Seasonal norm for {_MONTH_NAMES[query.travel_month - 1]}: "
                        f"avg high {avg_high}°C, avg low {avg_low}°C, "
                        f"~{seasonal['avg_precip_mm']} mm precip/month"
                    ),
                    "season_open_in_travel_month": dest.season_open[query.travel_month - 1],
                    "data_source": "seasonal_model",
                }
            else:
                # Use live forecast
                try:
                    wd = weather_api.get_forecast(
                        dest.coords[0],
                        dest.coords[1],
                        start,
                        days_per_dest,
                        destination_id=dest_id,
                    )
                except (weather_api.WeatherError, cache.CacheMiss) as exc:
                    per_dest[dest_id] = {
                        "name": dest.name,
                        "altitude_m": dest.altitude_m,
                        "error": str(exc),
                    }
                    continue

                avg_high = _avg(wd.daily_temp_max_c)
                avg_low = _avg(wd.daily_temp_min_c)
                total_precip = sum(wd.daily_precip_mm)
                peak_precip_prob = (
                    max(wd.daily_precip_prob) if wd.daily_precip_prob else 0.0
                )
                wet_days = sum(1 for p in wd.daily_precip_prob if p >= 60.0)

                per_dest[dest_id] = {
                    "name": dest.name,
                    "altitude_m": dest.altitude_m,
                    "avg_high_c": _r1(avg_high),
                    "avg_low_c": _r1(avg_low),
                    "total_precip_mm": _r1(total_precip),
                    "peak_precip_prob_pct": _r0(peak_precip_prob),
                    "wet_days_count": wet_days,
                    "summary": wd.summary,
                    "season_open_in_travel_month": dest.season_open[query.travel_month - 1],
                    "data_source": "live_forecast",
                }

        note = (
            "Using live Open-Meteo forecast."
            if not use_seasonal
            else (
                "Travel month is beyond Open-Meteo's 16-day horizon; "
                "using seasonal climate normals instead."
            )
        )

        return {
            "travel_month": query.travel_month,
            "travel_month_name": _MONTH_NAMES[query.travel_month - 1],
            "forecast_start": start.isoformat() if not use_seasonal else "N/A (seasonal)",
            "per_destination": per_dest,
            "note": note,
            "using_seasonal": use_seasonal,
        }

    def _check_blocker(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> Optional[str]:
        # Phase 1: do not hard-block on weather. We surface concerns instead.
        # If a destination is closed in the user's travel month per its
        # `season_open` array, that is a Road/Recommender concern, not Weather's.
        return None

    def _score(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        per_dest = analysis.get("per_destination", {})
        if not per_dest:
            return 5.0

        per_scores = []
        for data in per_dest.values():
            if "error" in data:
                per_scores.append(5.0)
                continue
            avg_high = data.get("avg_high_c") or 15.0
            total_precip = data.get("total_precip_mm") or 0.0
            wet_days = data.get("wet_days_count") or 0

            temp_penalty = 0.0
            if avg_high is None:
                temp_penalty = 0.0
            elif avg_high < -5:
                temp_penalty = 5.0
            elif avg_high < 0:
                temp_penalty = 3.0
            elif avg_high > 32:
                temp_penalty = 2.0

            precip_penalty = min(4.0, total_precip / 60.0)
            wet_penalty = min(3.0, wet_days * 0.6)

            s = 10.0 - temp_penalty - precip_penalty - wet_penalty
            per_scores.append(s)

        return statistics.mean(per_scores)

    def _confidence(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        per_dest = analysis.get("per_destination", {})
        if not per_dest:
            return 0.0
        good = sum(1 for d in per_dest.values() if "error" not in d)
        return good / len(per_dest)

    def _build_argue_prompt(
        self,
        analysis: Dict[str, Any],
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> str:
        per_dest = analysis.get("per_destination", {})
        lines = [
            f"Candidate: {candidate.label}",
            f"Destinations: {' -> '.join(candidate.destinations)}",
            (
                f"Trip days: {candidate.days}; travel month: "
                f"{analysis['travel_month_name']}; "
                f"group: {query.group_size} ({query.group_composition.value})"
            ),
            f"WeatherAgent deterministic score: {score:.1f}/10",
            f"Forecast window used: starts {analysis['forecast_start']}",
            "",
            "Per-destination weather summary:",
        ]
        for data in per_dest.values():
            if "error" in data:
                lines.append(
                    f"- {data.get('name', 'unknown')} "
                    f"(alt {data.get('altitude_m', '?')} m): "
                    f"forecast unavailable ({data['error']})"
                )
                continue
            season_note = (
                "open in travel month"
                if data.get("season_open_in_travel_month")
                else "CLOSED in travel month per season calendar"
            )
            lines.append(
                f"- {data['name']} (alt {data['altitude_m']} m, {season_note}): "
                f"avg high {data['avg_high_c']}°C, avg low {data['avg_low_c']}°C, "
                f"total precip {data['total_precip_mm']} mm, "
                f"peak precip-prob {data['peak_precip_prob_pct']}%, "
                f"{data['wet_days_count']} wet days"
            )
        lines.extend(
            [
                "",
                "Produce a JSON object with exactly two keys:",
                '  "reasons":  1-3 short bullets (<=25 words each) supporting this candidate',
                "              from a weather perspective.",
                '  "concerns": 1-3 short bullets (<=25 words each) flagging weather risks.',
                "",
                "Cite the data above. Do not invent forecasts. Reply with ONLY the JSON.",
            ]
        )
        return "\n".join(lines)

    def _templated_reasons(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        reasons = []
        per_dest = analysis.get("per_destination", {})
        warm_dests = []
        wet_dests = []
        error_dests = []

        for data in per_dest.values():
            if "error" in data:
                error_dests.append(data.get("name", "unknown"))
                continue
            avg_high = data.get("avg_high_c")
            wet_days = data.get("wet_days_count", 0)
            if avg_high is not None and avg_high > 25:
                warm_dests.append(data.get("name", "unknown"))
            if wet_days >= 2:
                wet_dests.append(data.get("name", "unknown"))

        if warm_dests:
            reasons.append(f"Pleasant temperatures expected in {', '.join(warm_dests[:2])}.")
        if not wet_dests and score >= 7.0:
            reasons.append("Dry conditions across the route — good for outdoor activities.")
        if not error_dests:
            reasons.append("Weather data available for all destinations on this route.")

        return reasons

    def _templated_concerns(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        concerns = []
        per_dest = analysis.get("per_destination", {})
        cold_dests = []
        wet_dests = []
        error_dests = []

        for data in per_dest.values():
            if "error" in data:
                error_dests.append(data.get("name", "unknown"))
                continue
            avg_high = data.get("avg_high_c")
            wet_days = data.get("wet_days_count", 0)
            if avg_high is not None and avg_high < 5:
                cold_dests.append(data.get("name", "unknown"))
            if wet_days >= 2:
                wet_dests.append(data.get("name", "unknown"))

        if cold_dests:
            concerns.append(f"Cold temperatures expected in {', '.join(cold_dests[:2])} — pack warm layers.")
        if wet_dests:
            concerns.append(f"Rainy days likely in {', '.join(wet_dests[:2])} — plan indoor backups.")
        if error_dests:
            concerns.append(f"Weather data unavailable for: {', '.join(error_dests)}.")

        return concerns

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _should_use_seasonal(query: UserQuery) -> bool:
        """
        Use seasonal model if the travel month is not the current month
        or the next month (Open-Meteo horizon is ~16 days).
        """
        today = date.today()
        current_month = today.month
        next_month = current_month + 1 if current_month < 12 else 1
        return query.travel_month not in (current_month, next_month)

    @staticmethod
    def _forecast_start_for_query(query: UserQuery, use_seasonal: bool = False) -> date:
        """
        Return the forecast start date. If using seasonal model, this is
        not used for API calls but we return a placeholder for consistency.
        """
        if use_seasonal:
            return date.today()
        return date.today() + timedelta(days=1)


def _avg(xs):
    if not xs:
        return None
    return sum(xs) / len(xs)


def _r1(x):
    return None if x is None else round(float(x), 1)


def _r0(x):
    return None if x is None else int(round(float(x)))


# Re-export for symmetry with the stub modules
__all__ = ["WeatherAgent", "LLMArgumentPayload"]
