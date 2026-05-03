"""
Orchestrator — Phase 3 full policy implementation.

Implements the complete section-7 policy:
    1. Hard-blocker elimination
    2. Weighted aggregate score over surviving candidates
    3. Epsilon=0.3 concentration tie-break
    4. Dissent detection (>2 point gap)
    5. Why-not summaries for runner-ups
    6. One Flash-Lite LLM call for natural-language synthesis
    7. Rich day-by-day plan expansion

Weights (fixed, editorial):
    SafetyAgent:  0.30
    BudgetAgent:  0.25
    WeatherAgent: 0.20
    RoadAgent:    0.15
    LocalAgent:   0.10
"""

from __future__ import annotations

from typing import Dict, List, Optional

from manzil.data_loader import load_destinations
from manzil.llm import Model
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
    "LocalAgent": 0.10,
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
                orchestrator_reasoning=self._all_blocked_reasoning(candidates, blockers),
                all_blocked=True,
            )

        aggregates = self._weighted_aggregate(surviving, arguments)
        winner = self._pick_winner(surviving, aggregates, arguments)
        dissent = self._detect_dissent(winner, arguments)
        why_not = self._generate_why_not(surviving, winner, arguments, aggregates)
        reasoning = self._llm_synthesize(winner, arguments, dissent, why_not)
        full_plan = self._expand_plan(winner, arguments)

        return DebateResult(
            winner=winner,
            full_plan=full_plan,
            scorecard=scorecard,
            blockers=blockers,
            dissenting_opinion=dissent,
            why_not=why_not,
            orchestrator_reasoning=reasoning,
            all_blocked=False,
        )

    # ------------------------------------------------------------------
    # Core policy helpers
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
                eff_weight = weight * arg.confidence
                total += arg.score * eff_weight
                weight_used += eff_weight
            out[c.candidate_id] = total / weight_used if weight_used > 0 else 0.0
        return out

    def _pick_winner(
        self,
        surviving: List[RouteCandidate],
        aggregates: Dict[str, float],
        arguments: List[AgentArgument],
    ) -> RouteCandidate:
        """
        Pick winner by aggregate score. If two candidates are within
        epsilon=0.3, apply concentration tie-break (higher concentration wins).
        """
        EPS = 0.3

        # Sort by aggregate score descending
        sorted_cands = sorted(
            surviving,
            key=lambda c: aggregates.get(c.candidate_id, 0.0),
            reverse=True,
        )

        if len(sorted_cands) == 1:
            return sorted_cands[0]

        top = sorted_cands[0]
        second = sorted_cands[1]
        top_score = aggregates.get(top.candidate_id, 0.0)
        second_score = aggregates.get(second.candidate_id, 0.0)

        if top_score - second_score > EPS:
            return top

        # Tie-break: concentration over breadth
        top_conc = self._concentration(top.candidate_id, arguments)
        second_conc = self._concentration(second.candidate_id, arguments)

        if second_conc > top_conc:
            return second
        return top

    def _concentration(self, candidate_id: str, arguments: List[AgentArgument]) -> float:
        """max(scores) - min(scores) for this candidate across all agents."""
        scores = [
            a.score for a in arguments if a.candidate_id == candidate_id
        ]
        if not scores:
            return 0.0
        return max(scores) - min(scores)

    def _detect_dissent(
        self,
        winner: RouteCandidate,
        arguments: List[AgentArgument],
    ) -> Optional[str]:
        """
        For each agent, find its top-scoring candidate. If the agent's
        score for the winner is >2 points below its top pick, surface dissent.
        """
        DISSENT_THRESHOLD = 2.0

        dissent_lines = []
        agent_names = {a.agent_name for a in arguments}

        for agent_name in agent_names:
            agent_args = [a for a in arguments if a.agent_name == agent_name]
            if not agent_args:
                continue

            top_arg = max(agent_args, key=lambda a: a.score)
            winner_arg = next(
                (a for a in agent_args if a.candidate_id == winner.candidate_id),
                None,
            )
            if winner_arg is None:
                continue

            gap = top_arg.score - winner_arg.score
            if gap > DISSENT_THRESHOLD:
                dissent_lines.append(
                    f"{agent_name} ranked {top_arg.candidate_id} highest "
                    f"({top_arg.score:.1f}/10) versus the winner's "
                    f"{winner_arg.score:.1f}/10 — a gap of {gap:.1f} points."
                )

        if not dissent_lines:
            return None
        return " ".join(dissent_lines)

    def _generate_why_not(
        self,
        surviving: List[RouteCandidate],
        winner: RouteCandidate,
        arguments: List[AgentArgument],
        aggregates: Dict[str, float],
    ) -> Dict[str, str]:
        """One-line explanation for each runner-up."""
        why_not: Dict[str, str] = {}
        for c in surviving:
            if c.candidate_id == winner.candidate_id:
                continue
            agg_score = aggregates.get(c.candidate_id, 0.0)
            winner_score = aggregates.get(winner.candidate_id, 0.0)
            delta = winner_score - agg_score

            # Find the agent that most hurt this candidate
            agent_args = [a for a in arguments if a.candidate_id == c.candidate_id]
            if agent_args:
                worst_agent = min(agent_args, key=lambda a: a.score)
                reason = (
                    f"Scored {agg_score:.1f}/10 aggregate vs winner's {winner_score:.1f}. "
                    f"{worst_agent.agent_name} gave it only {worst_agent.score:.1f}/10 "
                    f"— its weakest point."
                )
            else:
                reason = (
                    f"Scored {agg_score:.1f}/10 aggregate, {delta:.1f} points below the winner."
                )
            why_not[c.candidate_id] = reason
        return why_not

    def _all_blocked_reasoning(
        self,
        candidates: List[RouteCandidate],
        blockers: Dict[str, List[str]],
    ) -> str:
        lines = ["No candidate survived hard-blocker elimination."]
        for c in candidates:
            reasons = blockers.get(c.candidate_id, [])
            lines.append(
                f"- {c.candidate_id}: " + "; ".join(reasons)
            )
        lines.append("Returning structured failure rather than a bad recommendation.")
        return " ".join(lines)

    # ------------------------------------------------------------------
    # LLM synthesis
    # ------------------------------------------------------------------

    def _llm_synthesize(
        self,
        winner: RouteCandidate,
        arguments: List[AgentArgument],
        dissent: Optional[str],
        why_not: Dict[str, str],
    ) -> str:
        """
        One Flash-Lite call for the natural-language synthesis.
        Falls back to deterministic text if the LLM call fails.
        """
        from manzil import llm

        prompt_lines = [
            "You are the Orchestrator for a Pakistan travel-planning system.",
            "Synthesize a concise, honest recommendation paragraph (3-5 sentences).",
            "",
            f"WINNER: {winner.label} ({winner.candidate_id})",
            f"Destinations: {' -> '.join(winner.destinations)}",
            "",
            "Agent scores for the winner:",
        ]
        for arg in arguments:
            if arg.candidate_id == winner.candidate_id:
                prompt_lines.append(
                    f"- {arg.agent_name}: {arg.score:.1f}/10"
                )
                if arg.hard_blocker:
                    prompt_lines.append(f"  [BLOCKER: {arg.hard_blocker}]")
                if arg.supporting_reasons:
                    prompt_lines.append(f"  Reasons: {'; '.join(arg.supporting_reasons[:2])}")
                if arg.concerns:
                    prompt_lines.append(f"  Concerns: {'; '.join(arg.concerns[:2])}")

        if dissent:
            prompt_lines.extend([
                "",
                "DISSENTING OPINION:",
                dissent,
            ])

        if why_not:
            prompt_lines.extend([
                "",
                "WHY NOT THE RUNNER-UPS:",
            ])
            for cid, reason in why_not.items():
                prompt_lines.append(f"- {cid}: {reason}")

        prompt_lines.extend([
            "",
            "Write a single paragraph summarizing why the winner was chosen, "
            "acknowledging any dissent, and being honest about trade-offs. "
            "Do not invent facts. Keep it under 120 words.",
        ])

        prompt = "\n".join(prompt_lines)

        try:
            text = llm.complete(
                prompt,
                model=Model.FLASH_LITE,
                temperature=0.3,
            )
            return text.strip()
        except Exception as exc:
            # Fallback to deterministic synthesis
            return (
                f"{winner.label} was selected based on weighted aggregation "
                f"of agent scores. "
                + (f"Note: {dissent}" if dissent else "")
            )

    # ------------------------------------------------------------------
    # Plan expansion
    # ------------------------------------------------------------------

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
            for j in range(chunk):
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
                    travel_mode=travel_mode if day_index == 1 or j == 0 else None,
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
