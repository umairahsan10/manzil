"""
RoadAgent — Phase 1 stub.

Deterministic only. Computes aggregate drive-time across the route's
segments using `data/road_knowledge.json`. No LLM. No vetos in Phase 1.

Phase 3 promotes this to a full agent: pass-closure vetoes, landslide-risk
weighting, humane-driving caps, and an LLM-generated argument.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from manzil.agents.base import BaseAgent
from manzil.data_loader import load_road_knowledge
from manzil.schemas import LLMArgumentPayload, RouteCandidate, UserQuery


class RoadAgent(BaseAgent):
    name = "RoadAgent"
    uses_llm = False

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        rk = load_road_knowledge()
        segments = rk.get("segments", {})
        leg_lookup = self._leg_keys(query.origin_city, candidate.destinations)

        legs = []
        total_drive_h = 0.0
        max_leg_h = 0.0
        missing = []
        for key in leg_lookup:
            seg = segments.get(key)
            if seg is None:
                missing.append(key)
                continue
            legs.append({"leg": key, "hours": seg.get("drive_time_hours", 0.0)})
            total_drive_h += float(seg.get("drive_time_hours", 0.0))
            max_leg_h = max(max_leg_h, float(seg.get("drive_time_hours", 0.0)))

        return {
            "legs": legs,
            "total_drive_hours": round(total_drive_h, 1),
            "max_single_leg_hours": round(max_leg_h, 1),
            "missing_segments": missing,
            "humane_max_hours_per_day": rk.get("humane_drive_max_hours_per_day", 10),
        }

    def _check_blocker(self, analysis, candidate, query) -> Optional[str]:
        return None  # Phase 3 adds pass-closure + drive-time vetoes

    def _score(self, analysis, candidate, query) -> float:
        # 10 with zero road; -1 per 6 hours of total driving; floor at 1.
        total_h = analysis.get("total_drive_hours", 0.0)
        return max(1.0, 10.0 - total_h / 6.0)

    def _canned_argument(
        self, analysis, score, candidate, query
    ) -> LLMArgumentPayload:
        total_h = analysis.get("total_drive_hours", 0.0)
        max_h = analysis.get("max_single_leg_hours", 0.0)
        reasons = []
        concerns = []

        if total_h <= 12:
            reasons.append(
                f"Light total driving ({total_h:.0f} h) keeps the trip relaxed."
            )
        elif total_h <= 24:
            reasons.append(
                f"Reasonable total driving ({total_h:.0f} h) for the destinations."
            )
        else:
            concerns.append(
                f"Heavy total driving ({total_h:.0f} h) compresses sightseeing time."
            )

        if max_h >= 12:
            concerns.append(
                f"Longest single leg ~{max_h:.0f} h — consider splitting the day."
            )
        else:
            reasons.append(
                f"No single leg above {max_h:.0f} h — within humane-driving limits."
            )

        if analysis.get("missing_segments"):
            concerns.append(
                "Route knowledge incomplete for one or more legs; verify locally."
            )

        return LLMArgumentPayload(reasons=reasons[:3], concerns=concerns[:3])

    @staticmethod
    def _leg_keys(origin: str, destinations) -> list:
        keys = []
        prev = origin.lower()
        for dest in destinations:
            keys.append(f"{prev}__{dest}")
            prev = dest
        return keys


__all__ = ["RoadAgent"]
