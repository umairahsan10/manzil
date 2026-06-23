"""
SafetyAgent — Phase 3 real agent.

Deterministic analysis:
    - Altitude per destination from safety_knowledge.json
    - Group altitude tolerance threshold (kids <10 → 3,000m; 10–60 → 4,500m; >60 → 3,500m)
    - NOC requirement for foreign travellers
    - Nearest hospital / police proximity
    - Acclimatization day detection

Hard blockers:
    - Veto if any destination's altitude exceeds the group's threshold AND
      the trip lacks an acclimatization day.
    - Veto if a foreign traveller hits an NOC zone.

Score:
    - Penalize altitude headroom narrowness, NOC complexity, distance from medical care.

LLM argument:
    - Cites hospital proximity, low-altitude profile.
    - Concerns cite altitude exposure, NOC, isolation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from manzil.agents.base import BaseAgent
from manzil.data_loader import load_safety_knowledge
from manzil.schemas import (
    GroupType,
    RouteCandidate,
    UserQuery,
)


class SafetyAgent(BaseAgent):
    name = "SafetyAgent"
    uses_llm = True

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        sk = load_safety_knowledge()
        per_dest_data = sk.get("destinations", {})
        thresholds = sk.get("altitude_thresholds_m", {})
        noc_zones = set(sk.get("noc_zones_for_foreigners", []))
        acclim_rules = sk.get("altitude_acclimatization_rules", {})

        per_dest = []
        max_alt = 0
        max_alt_dest = ""
        total_hospital_dist = 0
        has_noc_zone = False
        has_acclimatization_day = self._has_acclimatization_day(candidate, query)

        for dest_id in candidate.destinations:
            entry = per_dest_data.get(dest_id, {})
            alt = int(entry.get("altitude_m", 0))
            hospital = entry.get("nearest_hospital", {})
            hospital_dist = hospital.get("distance_km", 0)
            noc_required = entry.get("noc_required", False)

            per_dest.append(
                {
                    "id": dest_id,
                    "altitude_m": alt,
                    "noc_required": noc_required,
                    "hospital_name": hospital.get("name", "unknown"),
                    "hospital_distance_km": hospital_dist,
                    "hospital_level": hospital.get("level", "unknown"),
                    "police_name": entry.get("nearest_police", {}).get("name", "unknown"),
                    "police_distance_km": entry.get("nearest_police", {}).get("distance_km", 0),
                }
            )

            if alt > max_alt:
                max_alt = alt
                max_alt_dest = dest_id

            total_hospital_dist += hospital_dist

            # Check if this destination is in an NOC zone
            if query.is_foreign_traveller and noc_required:
                has_noc_zone = True
            # Also check the noc_zones_for_foreigners list
            if query.is_foreign_traveller and dest_id in noc_zones:
                has_noc_zone = True

        threshold_key, threshold_m = self._threshold_for_query(query, thresholds)

        return {
            "per_destination": per_dest,
            "max_altitude_m": max_alt,
            "max_altitude_destination": max_alt_dest,
            "applied_threshold_key": threshold_key,
            "applied_threshold_m": threshold_m,
            "has_acclimatization_day": has_acclimatization_day,
            "has_noc_zone": has_noc_zone,
            "avg_hospital_distance_km": round(total_hospital_dist / max(1, len(per_dest)), 1),
            "group_composition": query.group_composition.value,
        }

    def _check_blocker(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> Optional[str]:
        # Altitude blocker
        threshold = analysis.get("applied_threshold_m")
        max_alt = analysis.get("max_altitude_m", 0)
        has_acclim = analysis.get("has_acclimatization_day", False)

        if threshold and max_alt > threshold and not has_acclim:
            dest = analysis.get("max_altitude_destination", "?")
            return (
                f"Altitude {max_alt} m at '{dest}' exceeds the "
                f"{analysis['applied_threshold_key']} threshold of {threshold} m "
                f"without an acclimatization day."
            )

        # NOC blocker for foreign travellers
        if analysis.get("has_noc_zone") and query.is_foreign_traveller:
            return (
                "Route includes an NOC-restricted zone; foreign travellers "
                "require special permits."
            )

        return None

    def _score(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        threshold = analysis.get("applied_threshold_m") or 4500
        max_alt = analysis.get("max_altitude_m", 0)
        avg_hospital_dist = analysis.get("avg_hospital_distance_km", 0)
        has_noc = analysis.get("has_noc_zone", False)
        is_solo = query.group_composition.value == "solo"

        # Altitude headroom: ratio of max_alt to threshold
        if max_alt <= 0:
            alt_score = 7.0
        else:
            ratio = max_alt / threshold
            if ratio >= 1.0:
                alt_score = 0.0
            else:
                alt_score = max(2.0, 10.0 - 6.0 * ratio)

        # Hospital proximity penalty
        hospital_penalty = min(3.0, avg_hospital_dist / 20.0)

        # NOC penalty
        noc_penalty = 1.5 if has_noc else 0.0

        # Solo-travel penalty: solo travellers face higher risk on remote or high-altitude routes
        solo_penalty = 0.0
        if is_solo:
            if max_alt > 2200:
                solo_penalty += 1.0
            if avg_hospital_dist > 30:
                solo_penalty += 1.0

        score = alt_score - hospital_penalty - noc_penalty - solo_penalty
        return score

    def _confidence(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        per_dest = analysis.get("per_destination", [])
        if not per_dest:
            return 0.5
        return 1.0

    def _build_argue_prompt(
        self,
        analysis: Dict[str, Any],
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> str:
        lines = [
            f"Candidate: {candidate.label}",
            f"Destinations: {' -> '.join(candidate.destinations)}",
            f"Group: {query.group_size} people ({analysis['group_composition']})",
            f"Foreign traveller: {'yes' if query.is_foreign_traveller else 'no'}",
            f"SafetyAgent deterministic score: {score:.1f}/10",
            "",
            f"Max altitude on route: {analysis['max_altitude_m']} m "
            f"at {analysis['max_altitude_destination']}",
            f"Applied threshold: {analysis['applied_threshold_key']} = "
            f"{analysis['applied_threshold_m']} m",
            f"Has acclimatization day: {analysis['has_acclimatization_day']}",
            f"Average distance to nearest hospital: {analysis['avg_hospital_distance_km']} km",
            f"Includes NOC zone: {analysis['has_noc_zone']}",
            "",
            "Per-destination safety data:",
        ]
        for d in analysis.get("per_destination", []):
            lines.append(
                f"- {d['id']}: alt {d['altitude_m']} m, "
                f"hospital {d['hospital_name']} ({d['hospital_distance_km']} km, "
                f"{d['hospital_level']}), "
                f"police {d['police_name']} ({d['police_distance_km']} km)"
            )

        lines.extend(
            [
                "",
                "Produce a JSON object with exactly two keys:",
                '  "reasons":  1-3 short bullets (<=25 words each) supporting this candidate',
                "              from a safety perspective.",
                '  "concerns": 1-3 short bullets (<=25 words each) flagging safety risks.',
                "",
                "Cite the data above. Do not invent hospital names or distances. "
                "Reply with ONLY the JSON.",
            ]
        )
        return "\n".join(lines)

    def _templated_reasons(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        reasons = []
        threshold = analysis.get("applied_threshold_m", 4500)
        max_alt = analysis.get("max_altitude_m", 0)
        avg_hospital = analysis.get("avg_hospital_distance_km", 0)
        has_noc = analysis.get("has_noc_zone", False)
        has_acclim = analysis.get("has_acclimatization_day", False)
        is_solo = query.group_composition.value == "solo"

        if max_alt < threshold:
            headroom = threshold - max_alt
            reasons.append(f"All destinations stay well below the altitude threshold with {headroom}m of headroom.")
        if has_acclim:
            reasons.append("Route includes an acclimatization day — good for altitude adjustment.")
        if avg_hospital < 15:
            reasons.append(f"Medical facilities are nearby (avg {avg_hospital:.0f} km to nearest hospital).")
        if not has_noc:
            reasons.append("No NOC permit required — simpler logistics for this route.")
        if is_solo and max_alt <= 2500 and avg_hospital < 20:
            reasons.append("Well-connected route suitable for solo travel — medical access and moderate altitude.")

        return reasons

    def _templated_concerns(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        concerns = []
        threshold = analysis.get("applied_threshold_m", 4500)
        max_alt = analysis.get("max_altitude_m", 0)
        avg_hospital = analysis.get("avg_hospital_distance_km", 0)
        has_noc = analysis.get("has_noc_zone", False)
        has_acclim = analysis.get("has_acclimatization_day", False)
        is_solo = query.group_composition.value == "solo"

        if max_alt > threshold * 0.8:
            concerns.append(f"Maximum altitude ({max_alt}m) approaches the safety threshold ({threshold}m).")
        if avg_hospital > 30:
            concerns.append(f"Hospitals are distant (avg {avg_hospital:.0f} km) — plan for emergencies.")
        if has_noc:
            concerns.append("NOC permit required — foreign travellers need advance paperwork.")
        if not has_acclim and max_alt > 3000:
            concerns.append("No acclimatization day included — watch for altitude sickness symptoms.")
        if is_solo and max_alt > 2200:
            concerns.append("Solo traveller on a route with notable altitude — ensure emergency contacts and travel insurance.")
        if is_solo and avg_hospital > 30:
            concerns.append("Remote route with limited medical access — solo travellers should carry a first-aid kit.")

        return concerns

    @staticmethod
    def _threshold_for_query(query: UserQuery, thresholds: Dict[str, int]):
        # altitude_sensitive overrides everything with the lowest threshold
        if query.altitude_sensitive:
            return ("altitude_sensitive", thresholds.get("elderly_over_60", 3500))
        if query.elderly_in_group:
            return ("elderly_over_60", thresholds.get("elderly_over_60", 3500))
        if query.kids_in_group or query.group_composition == GroupType.FAMILY:
            return ("kids_under_10", thresholds.get("kids_under_10", 3000))
        if query.group_composition == GroupType.MIXED:
            return ("kids_10_to_18", thresholds.get("kids_10_to_18", 4000))
        return ("general_adult", thresholds.get("general_adult", 4500))

    @staticmethod
    def _has_acclimatization_day(candidate: RouteCandidate, query: UserQuery) -> bool:
        """
        Heuristic: an acclimatization day exists if the trip is >= 7 days
        AND the first destination is <= 3,000 m AND any subsequent
        destination is > 3,000 m. This gives the group at least one
        low-altitude overnight before ascending.
        """
        if candidate.days < 5:
            return False
        from manzil.data_loader import load_safety_knowledge

        sk = load_safety_knowledge()
        per_dest = sk.get("destinations", {})

        if not candidate.destinations:
            return False

        first_alt = per_dest.get(candidate.destinations[0], {}).get("altitude_m", 0)
        if first_alt > 3000:
            return False

        # Check if any later destination is significantly higher
        for dest_id in candidate.destinations[1:]:
            alt = per_dest.get(dest_id, {}).get("altitude_m", 0)
            if alt > 3500:
                return True

        return False


__all__ = ["SafetyAgent"]
