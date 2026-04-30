"""
SafetyAgent — Phase 1 stub.

Deterministic only. Reads altitude per destination from `safety_knowledge.json`
and applies a basic altitude-vs-group threshold check. No LLM.

This is the only Phase-1 stub that can issue a hard blocker, because
Safety's veto is a core product commitment (see Readme §6) and it would be
dishonest to ship a debate that ignored it.

Phase 3 promotes this to a full agent: NOC zones, hospital/police lookup,
acclimatization rules, and an LLM-generated argument.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from manzil.agents.base import BaseAgent
from manzil.data_loader import load_safety_knowledge
from manzil.schemas import GroupType, LLMArgumentPayload, RouteCandidate, UserQuery


class SafetyAgent(BaseAgent):
    name = "SafetyAgent"
    uses_llm = False

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        sk = load_safety_knowledge()
        per_dest_data = sk.get("destinations", {})
        thresholds = sk.get("altitude_thresholds_m", {})

        per_dest = []
        max_alt = 0
        max_alt_name = ""
        for dest_id in candidate.destinations:
            entry = per_dest_data.get(dest_id, {})
            alt = int(entry.get("altitude_m", 0))
            per_dest.append({"id": dest_id, "altitude_m": alt})
            if alt > max_alt:
                max_alt = alt
                max_alt_name = dest_id

        threshold_key, threshold_m = self._threshold_for_query(query, thresholds)

        return {
            "per_destination": per_dest,
            "max_altitude_m": max_alt,
            "max_altitude_destination": max_alt_name,
            "applied_threshold_key": threshold_key,
            "applied_threshold_m": threshold_m,
        }

    def _check_blocker(self, analysis, candidate, query) -> Optional[str]:
        threshold = analysis.get("applied_threshold_m")
        max_alt = analysis.get("max_altitude_m", 0)
        if threshold and max_alt > threshold:
            dest = analysis.get("max_altitude_destination", "?")
            return (
                f"Altitude {max_alt} m at '{dest}' exceeds the "
                f"{analysis['applied_threshold_key']} threshold of {threshold} m."
            )
        return None

    def _score(self, analysis, candidate, query) -> float:
        threshold = analysis.get("applied_threshold_m") or 4500
        max_alt = analysis.get("max_altitude_m", 0)
        # 10 with plenty of altitude headroom; degrades as we approach threshold.
        if max_alt <= 0:
            return 7.0
        ratio = max_alt / threshold
        if ratio >= 1.0:
            return 0.0
        return max(2.0, 10.0 - 8.0 * ratio)

    def _canned_argument(
        self, analysis, score, candidate, query
    ) -> LLMArgumentPayload:
        max_alt = analysis.get("max_altitude_m", 0)
        threshold = analysis.get("applied_threshold_m") or 4500
        threshold_key = analysis.get("applied_threshold_key", "general")

        reasons = []
        concerns = []
        if max_alt and max_alt < threshold * 0.6:
            reasons.append(
                f"Highest point is only {max_alt} m — well below the "
                f"{threshold_key} threshold of {threshold} m."
            )
        elif max_alt < threshold:
            reasons.append(
                f"Highest point {max_alt} m fits within the "
                f"{threshold_key} threshold ({threshold} m), with margin to spare."
            )

        if max_alt >= threshold * 0.85 and max_alt < threshold:
            concerns.append(
                f"Highest point {max_alt} m is close to the {threshold_key} "
                f"threshold; consider an acclimatization day."
            )
        if not reasons and not concerns:
            reasons.append("Standard mountain-travel safety profile for the region.")

        return LLMArgumentPayload(reasons=reasons[:3], concerns=concerns[:3])

    @staticmethod
    def _threshold_for_query(query: UserQuery, thresholds: Dict[str, int]):
        if query.group_composition == GroupType.FAMILY:
            return ("kids_under_10", thresholds.get("kids_under_10", 3000))
        if query.group_composition == GroupType.MIXED:
            return ("kids_10_to_18", thresholds.get("kids_10_to_18", 4000))
        return ("general_adult", thresholds.get("general_adult", 4500))


__all__ = ["SafetyAgent"]
