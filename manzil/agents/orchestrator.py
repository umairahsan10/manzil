"""
Orchestrator — Phase 1 minimal version.

Implements only what is needed to render a winner page:
    - hard-blocker elimination (a candidate with one or more blockers loses)
    - weighted aggregate score over surviving candidates
    - winner selection
    - a simple day-by-day plan expansion

Phase 3 promotes this to the full §7 policy:
    - epsilon=0.3 concentration tie-break
    - dissent detection
    - why-not summaries for runner-ups
    - one Flash LLM call for natural-language synthesis
"""

from __future__ import annotations

from typing import Dict, List, Optional

from manzil.data_loader import load_destinations
from manzil.schemas import (
    AgentArgument,
    DayByDayPlan,
    DayPlan,
    DayStop,
    DebateResult,
    RouteCandidate,
    TravelMode,
)

# Editorial weights — fixed in the project version (Readme §5).
DEFAULT_WEIGHTS: Dict[str, float] = {
    "SafetyAgent": 0.30,
    "BudgetAgent": 0.25,
    "WeatherAgent": 0.20,
    "RoadAgent": 0.15,
    "LocalExperienceAgent": 0.10,
}


class Orchestrator:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = dict(weights or DEFAULT_WEIGHTS)

    def synthesize(
        self,
        candidates: List[RouteCandidate],
        arguments: List[AgentArgument],
    ) -> DebateResult:
        scorecard = self._build_scorecard(arguments)
        blockers = self._collect_blockers(arguments)

        surviving = [
            c for c in candidates if not blockers.get(c.candidate_id)
        ]

        if not surviving:
            return DebateResult(
                winner=None,
                full_plan=None,
                scorecard=scorecard,
                blockers=blockers,
                dissenting_opinion=None,
                why_not={},
                orchestrator_reasoning=(
                    "No candidate survived hard-blocker elimination. "
                    "Returning structured failure rather than a bad recommendation."
                ),
                all_blocked=True,
            )

        aggregates = self._weighted_aggregate(surviving, arguments)
        winner = max(surviving, key=lambda c: aggregates.get(c.candidate_id, 0.0))

        full_plan = self._expand_plan(winner, arguments)

        return DebateResult(
            winner=winner,
            full_plan=full_plan,
            scorecard=scorecard,
            blockers=blockers,
            dissenting_opinion=None,  # Phase 3
            why_not={},  # Phase 3
            orchestrator_reasoning=(
                f"Winner: {winner.label}. "
                f"Weighted aggregate score: {aggregates[winner.candidate_id]:.2f}/10. "
                "Phase-1 orchestrator: dissent detection and why-not summaries land in Phase 3."
            ),
            all_blocked=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_scorecard(
        self, arguments: List[AgentArgument]
    ) -> Dict[str, Dict[str, float]]:
        scorecard: Dict[str, Dict[str, float]] = {}
        for arg in arguments:
            scorecard.setdefault(arg.agent_name, {})[arg.candidate_id] = arg.score
        return scorecard

    def _collect_blockers(
        self, arguments: List[AgentArgument]
    ) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for arg in arguments:
            if arg.hard_blocker:
                out.setdefault(arg.candidate_id, []).append(
                    f"{arg.agent_name}: {arg.hard_blocker}"
                )
        return out

    def _weighted_aggregate(
        self,
        candidates: List[RouteCandidate],
        arguments: List[AgentArgument],
    ) -> Dict[str, float]:
        # Build a dict (candidate_id, agent_name) -> argument
        by_pair: Dict[tuple, AgentArgument] = {}
        for arg in arguments:
            by_pair[(arg.candidate_id, arg.agent_name)] = arg

        out: Dict[str, float] = {}
        for c in candidates:
            total = 0.0
            weight_used = 0.0
            for agent_name, weight in self.weights.items():
                arg = by_pair.get((c.candidate_id, agent_name))
                if arg is None:
                    continue
                # Down-weight low-confidence arguments
                eff_weight = weight * arg.confidence
                total += arg.score * eff_weight
                weight_used += eff_weight
            out[c.candidate_id] = total / weight_used if weight_used > 0 else 0.0
        return out

    def _expand_plan(
        self,
        winner: RouteCandidate,
        arguments: List[AgentArgument],
    ) -> DayByDayPlan:
        destinations_by_id = load_destinations()

        n_dests = max(1, len(winner.destinations))
        days_per_dest, leftover = divmod(winner.days, n_dests)
        if days_per_dest == 0:
            days_per_dest = 1
            leftover = 0

        day_index = 1
        days: List[DayPlan] = []

        for i, dest_id in enumerate(winner.destinations):
            dest = destinations_by_id.get(dest_id)
            chunk = days_per_dest + (1 if i < leftover else 0)
            for _ in range(chunk):
                stop = DayStop(
                    destination_id=dest_id,
                    name=dest.name if dest else dest_id,
                    activities=list((dest.activity_tags if dest else [])[:2]),
                    local_tip=None,
                )
                travel_mode = (
                    winner.travel_modes[i] if i < len(winner.travel_modes) else None
                )
                day = DayPlan(
                    day_index=day_index,
                    stops=[stop],
                    travel_mode=travel_mode if day_index == 1 or _ == 0 else None,
                    drive_time_hours=None,
                    estimated_cost=int(winner.estimated_cost / max(1, winner.days)),
                    weather_note=self._note_for(arguments, "WeatherAgent", winner.candidate_id),
                    road_note=self._note_for(arguments, "RoadAgent", winner.candidate_id),
                    safety_note=self._note_for(arguments, "SafetyAgent", winner.candidate_id),
                )
                days.append(day)
                day_index += 1

        # Trim or pad to exactly winner.days
        days = days[: winner.days]

        return DayByDayPlan(
            candidate_id=winner.candidate_id,
            days=days,
            total_cost=winner.estimated_cost,
        )

    @staticmethod
    def _note_for(
        arguments: List[AgentArgument], agent_name: str, candidate_id: str
    ) -> Optional[str]:
        for arg in arguments:
            if arg.agent_name == agent_name and arg.candidate_id == candidate_id:
                if arg.supporting_reasons:
                    return arg.supporting_reasons[0]
                if arg.concerns:
                    return arg.concerns[0]
                return None
        return None


__all__ = ["Orchestrator", "DEFAULT_WEIGHTS"]
