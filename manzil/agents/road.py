"""
RoadAgent — Phase 3 real agent.

Deterministic analysis:
    - Looks up each pass on the route in road_knowledge.json
    - Computes drive-time per day from the distance matrix
    - Aggregates landslide risk for the chosen month

Hard blockers:
    - Veto if any pass on the route has open_months[month-1] == False
    - Veto if any single day's drive exceeds 12 hours (humane-driving rule)  [DISABLED FOR DEMO]

Score:
    - Linear from average drive-time per day and aggregate landslide risk

LLM argument:
    - Emphasizes "smooth highway segments" / "well-paved KKH"
    - Concerns surface "monsoon landslide history" / "long Day 3 drive"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from manzil.agents.base import BaseAgent
from manzil.schemas import RouteCandidate, UserQuery
from manzil.tools import route_calc


class RoadAgent(BaseAgent):
    name = "RoadAgent"
    uses_llm = True

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        origin = query.origin_city.lower()
        month = query.travel_month

        # Passes on the route
        passes = route_calc.passes_on_route(origin, candidate.destinations)

        # Segment details
        segments = route_calc.route_segments(origin, candidate.destinations)

        # Drive time per day (total / days, plus max single leg)
        total_drive_h = route_calc.total_drive_time(origin, candidate.destinations)
        avg_drive_per_day = total_drive_h / max(1, candidate.days)
        max_leg_h = route_calc.max_single_leg_drive_time(origin, candidate.destinations)

        # Landslide risk
        max_landslide_risk = route_calc.landslide_risk_for_month(
            origin, candidate.destinations, month
        )

        # Missing segments?
        missing = [s["leg_key"] for s in segments if s.get("missing")]

        # Per-destination road risk for the trip detail page
        per_dest_risk = []
        for seg in segments:
            if seg.get("missing"):
                continue
            dest_id = seg.get("to", "")
            landslide = seg.get("landslide_risk", 0.0)
            drive_h = seg.get("drive_time_hours", 0.0)
            passes_on_seg = [p for p in passes if p.get("altitude_m", 0) > 3000]
            if landslide > 0.4 or drive_h > 10:
                risk = "high"
            elif landslide > 0.2 or drive_h > 6 or passes_on_seg:
                risk = "moderate"
            else:
                risk = "low"
            reasons = []
            if landslide > 0.3:
                reasons.append(f"Landslide risk {landslide:.0%}")
            if drive_h > 8:
                reasons.append(f"Long drive {drive_h:.1f}h")
            if passes_on_seg:
                reasons.append(f"{len(passes_on_seg)} high pass(es) on route")
            per_dest_risk.append({
                "destination_id": dest_id,
                "segment": f"{seg.get('from', '?')} → {dest_id}",
                "risk_level": risk,
                "risk_reasons": reasons,
            })

        return {
            "travel_month": month,
            "total_drive_hours": round(total_drive_h, 1),
            "avg_drive_per_day_hours": round(avg_drive_per_day, 1),
            "max_single_leg_hours": round(max_leg_h, 1),
            "max_landslide_risk": round(max_landslide_risk, 2),
            "passes": passes,
            "segments": segments,
            "missing_segments": missing,
            "per_destination": per_dest_risk,
        }

    def _check_blocker(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> Optional[str]:
        month_idx = query.travel_month - 1  # 0-based

        # road_trip_only: veto any candidate using air travel
        if getattr(query, "road_trip_only", False):
            air_modes = [m for m in candidate.travel_modes if m.value in ("air", "hybrid")]
            if air_modes:
                return (
                    "Route includes flight segments but user requested road-trip only."
                )

        # Check pass closures
        for p in analysis.get("passes", []):
            open_months = p.get("open_months", [])
            if month_idx < len(open_months) and not open_months[month_idx]:
                return (
                    f"{p.get('name', p['pass_id'])} is closed in "
                    f"month {query.travel_month}."
                )

        return None

    def _score(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        avg_drive = analysis.get("avg_drive_per_day_hours", 0.0)
        landslide_risk = analysis.get("max_landslide_risk", 0.0)
        missing = analysis.get("missing_segments", [])

        # Penalize avg drive time: -1 per 3 hours, max penalty 6
        drive_penalty = min(6.0, avg_drive / 3.0)

        # Penalize landslide risk: up to 3 points
        landslide_penalty = landslide_risk * 3.0

        # Missing knowledge penalty
        missing_penalty = 2.0 if missing else 0.0

        # Motion sickness: penalize routes with high-altitude winding passes
        motion_sickness_penalty = 0.0
        if getattr(query, "motion_sickness", False):
            high_passes = [p for p in analysis.get("passes", []) if p.get("altitude_m", 0) > 3000]
            motion_sickness_penalty = min(3.0, len(high_passes) * 1.0)

        score = 10.0 - drive_penalty - landslide_penalty - missing_penalty - motion_sickness_penalty
        return score

    def _confidence(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        missing = analysis.get("missing_segments", [])
        if missing:
            return 0.6
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
            f"Origin: {query.origin_city}",
            f"Trip days: {candidate.days}; travel month: {analysis['travel_month']}",
            f"RoadAgent deterministic score: {score:.1f}/10",
            "",
            "Route analysis:",
            f"- Total drive time: {analysis['total_drive_hours']:.1f} h",
            f"- Average per day: {analysis['avg_drive_per_day_hours']:.1f} h",
            f"- Max single leg: {analysis['max_single_leg_hours']:.1f} h",
            f"- Peak landslide risk this month: {analysis['max_landslide_risk']:.0%}",
        ]

        passes = analysis.get("passes", [])
        if passes:
            lines.append("- Passes on route:")
            for p in passes:
                month_idx = query.travel_month - 1
                open_months = p.get("open_months", [])
                status = (
                    "OPEN"
                    if month_idx < len(open_months) and open_months[month_idx]
                    else "CLOSED"
                )
                lines.append(
                    f"  * {p.get('name', p['pass_id'])} "
                    f"(alt {p.get('altitude_m', '?')} m) — {status}"
                )
        else:
            lines.append("- No major mountain passes on this route.")

        missing = analysis.get("missing_segments", [])
        if missing:
            lines.append(f"- WARNING: Missing road data for segments: {', '.join(missing)}")

        lines.extend(
            [
                "",
                "Produce a JSON object with exactly two keys:",
                '  "reasons":  1-3 short bullets (<=25 words each) supporting this candidate',
                "              from a road-quality / drive-time perspective.",
                '  "concerns": 1-3 short bullets (<=25 words each) flagging road risks.',
                "",
                "Cite the data above. Do not invent road conditions. Reply with ONLY the JSON.",
            ]
        )
        return "\n".join(lines)

    def _templated_reasons(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        reasons = []
        avg_drive = analysis.get("avg_drive_per_day_hours", 0.0)
        passes = analysis.get("passes", [])
        missing = analysis.get("missing_segments", [])

        if avg_drive < 4:
            reasons.append(f"Light driving load at just {avg_drive:.1f} hours per day on average.")
        elif avg_drive < 6:
            reasons.append(f"Moderate driving at {avg_drive:.1f} hours daily — comfortable for most groups.")

        month_idx = query.travel_month - 1
        open_passes = [
            p for p in passes
            if month_idx < len(p.get("open_months", [])) and p["open_months"][month_idx]
        ]
        if open_passes:
            names = ", ".join(p.get("name", p["pass_id"]) for p in open_passes[:2])
            reasons.append(f"Major passes ({names}) are open this month.")

        if not missing:
            reasons.append("Complete road data available for every segment of this route.")

        return reasons

    def _templated_concerns(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        concerns = []
        max_leg = analysis.get("max_single_leg_hours", 0.0)
        landslide = analysis.get("max_landslide_risk", 0.0)
        missing = analysis.get("missing_segments", [])

        if max_leg > 8:
            concerns.append(f"Longest driving leg is {max_leg:.1f} hours — consider scheduling a break.")
        if landslide > 0.3:
            concerns.append(f"Elevated landslide risk this month ({landslide:.0%}) — monitor weather forecasts closely.")
        if missing:
            concerns.append(f"Missing road data for segments: {', '.join(missing)}.")

        return concerns


__all__ = ["RoadAgent"]
