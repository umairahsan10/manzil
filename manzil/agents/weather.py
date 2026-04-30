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

import statistics
from datetime import date, timedelta
from typing import Any, Dict, Optional

from manzil.agents.base import BaseAgent
from manzil.data_loader import load_destinations
from manzil.schemas import LLMArgumentPayload, RouteCandidate, UserQuery
from manzil.tools import cache, weather_api

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
        start = self._forecast_start_for_query(query)
        days_per_dest = max(1, candidate.days // max(1, len(candidate.destinations)))
        days_per_dest = min(days_per_dest, 7)  # cap per-destination forecast

        per_dest: Dict[str, Dict[str, Any]] = {}
        for dest_id in candidate.destinations:
            dest = destinations_by_id.get(dest_id)
            if dest is None:
                per_dest[dest_id] = {"error": f"unknown destination id {dest_id!r}"}
                continue
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
            }

        return {
            "travel_month": query.travel_month,
            "travel_month_name": _MONTH_NAMES[query.travel_month - 1],
            "forecast_start": start.isoformat(),
            "per_destination": per_dest,
            "note": (
                "Open-Meteo's free forecast horizon is 16 days; we use a near-term "
                "proxy when the travel month is further out. A seasonal model is "
                "scheduled for Phase 3."
            ),
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
            per_scores.append(max(0.0, min(10.0, s)))

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _forecast_start_for_query(query: UserQuery) -> date:
        """
        For Phase 1: always use tomorrow as the forecast start. Open-Meteo
        only gives 16 forward days, so requesting "2026-07-15" as a start
        when today is 2026-04-30 would return zero data. The agent's
        analysis surfaces this via the `note` field; Phase 3 swaps in a
        seasonal model for distant travel months.
        """
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
