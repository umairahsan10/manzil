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
    AgentScoreDetail,
    CandidateAggregate,
    DayByDayPlan,
    DayPlan,
    DayStop,
    DebateResult,
    DebateTrace,
    DissentTrace,
    OrchestratorTrace,
    RouteCandidate,
    TieBreakTrace,
    WhyNotTrace,
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

        orch_trace = OrchestratorTrace(
            weights_used=dict(self.weights),
            surviving_ids=[c.candidate_id for c in surviving],
            blocked_ids=[c.candidate_id for c in candidates if blockers.get(c.candidate_id)],
        )

        if not surviving:
            return DebateResult(
                winner=None,
                full_plan=None,
                scorecard=scorecard,
                blockers=blockers,
                arguments=arguments,
                dissenting_opinion=None,
                why_not={},
                orchestrator_reasoning=self._all_blocked_reasoning(candidates, blockers),
                all_blocked=True,
                debate_trace=DebateTrace(
                    arguments=arguments,
                    orchestrator=orch_trace,
                ),
            )

        aggregates, cand_aggs = self._weighted_aggregate_with_trace(surviving, arguments)
        orch_trace.candidates = cand_aggs

        winner, tie_trace = self._pick_winner_with_trace(surviving, aggregates, arguments)
        orch_trace.tie_break = tie_trace
        orch_trace.final_winner_id = winner.candidate_id if winner else None

        dissent, dissent_trace = self._detect_dissent_with_trace(winner, arguments)
        orch_trace.dissent = dissent_trace

        why_not, why_not_traces = self._generate_why_not_with_trace(
            surviving, winner, arguments, aggregates
        )
        orch_trace.why_not = why_not_traces

        reasoning = self._llm_synthesize(winner, arguments, dissent, why_not)
        full_plan = self._expand_plan(winner, arguments)

        return DebateResult(
            winner=winner,
            full_plan=full_plan,
            scorecard=scorecard,
            blockers=blockers,
            arguments=arguments,
            dissenting_opinion=dissent,
            why_not=why_not,
            orchestrator_reasoning=reasoning,
            all_blocked=False,
            debate_trace=DebateTrace(
                arguments=arguments,
                orchestrator=orch_trace,
            ),
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
        agg, _ = self._weighted_aggregate_with_trace(candidates, arguments)
        return agg

    def _weighted_aggregate_with_trace(
        self,
        candidates: List[RouteCandidate],
        arguments: List[AgentArgument],
    ) -> tuple[Dict[str, float], List[CandidateAggregate]]:
        by_pair: Dict[tuple, AgentArgument] = {}
        for arg in arguments:
            by_pair[(arg.candidate_id, arg.agent_name)] = arg

        out: Dict[str, float] = {}
        cand_aggs: List[CandidateAggregate] = []
        for c in candidates:
            total = 0.0
            weight_used = 0.0
            details: List[AgentScoreDetail] = []
            for agent_name, weight in self.weights.items():
                arg = by_pair.get((c.candidate_id, agent_name))
                if arg is None:
                    continue
                eff_weight = weight * arg.confidence
                contribution = arg.score * eff_weight
                total += contribution
                weight_used += eff_weight
                details.append(
                    AgentScoreDetail(
                        agent_name=agent_name,
                        weight=weight,
                        raw_score=arg.score,
                        confidence=arg.confidence,
                        effective_weight=round(eff_weight, 3),
                        contribution=round(contribution, 3),
                    )
                )
            agg_score = total / weight_used if weight_used > 0 else 0.0
            out[c.candidate_id] = agg_score
            cand_aggs.append(
                CandidateAggregate(
                    candidate_id=c.candidate_id,
                    candidate_label=c.label,
                    agent_details=details,
                    total_weighted=round(total, 3),
                    total_effective_weight=round(weight_used, 3),
                    aggregate_score=round(agg_score, 3),
                    concentration=round(self._concentration(c.candidate_id, arguments), 3),
                )
            )
        return out, cand_aggs

    def _pick_winner(
        self,
        surviving: List[RouteCandidate],
        aggregates: Dict[str, float],
        arguments: List[AgentArgument],
    ) -> RouteCandidate:
        winner, _ = self._pick_winner_with_trace(surviving, aggregates, arguments)
        return winner

    def _pick_winner_with_trace(
        self,
        surviving: List[RouteCandidate],
        aggregates: Dict[str, float],
        arguments: List[AgentArgument],
    ) -> tuple[RouteCandidate, TieBreakTrace]:
        """
        Pick winner by aggregate score. If two candidates are within
        epsilon=0.3, apply concentration tie-break (lower concentration wins).
        """
        EPS = 0.3

        # Sort by aggregate score descending
        sorted_cands = sorted(
            surviving,
            key=lambda c: aggregates.get(c.candidate_id, 0.0),
            reverse=True,
        )

        if len(sorted_cands) == 1:
            trace = TieBreakTrace(
                epsilon=EPS,
                top_candidate_id=sorted_cands[0].candidate_id,
                second_candidate_id="",
                top_score=round(aggregates.get(sorted_cands[0].candidate_id, 0.0), 3),
                second_score=0.0,
                gap=999.0,
                triggered=False,
                top_concentration=0.0,
                second_concentration=0.0,
                winner_id=sorted_cands[0].candidate_id,
                reason="Only one surviving candidate — no tie-break needed.",
            )
            return sorted_cands[0], trace

        top = sorted_cands[0]
        second = sorted_cands[1]
        top_score = aggregates.get(top.candidate_id, 0.0)
        second_score = aggregates.get(second.candidate_id, 0.0)
        gap = top_score - second_score

        top_conc = self._concentration(top.candidate_id, arguments)
        second_conc = self._concentration(second.candidate_id, arguments)

        if gap > EPS:
            winner = top
            reason = (
                f"Top candidate {top.candidate_id} ({top_score:.2f}) beat "
                f"{second.candidate_id} ({second_score:.2f}) by {gap:.2f}, "
                f"exceeding epsilon={EPS}. No tie-break needed."
            )
        else:
            # Tie-break: lower concentration wins (agents agreed more consistently)
            if second_conc < top_conc:
                winner = second
                reason = (
                    f"Gap {gap:.2f} <= epsilon {EPS}. Tie-break triggered. "
                    f"{second.candidate_id} has lower concentration ({second_conc:.2f}) "
                    f"vs {top.candidate_id} ({top_conc:.2f}) → agents agreed more. "
                    f"Winner flipped to {second.candidate_id}."
                )
            else:
                winner = top
                reason = (
                    f"Gap {gap:.2f} <= epsilon {EPS}. Tie-break triggered. "
                    f"{top.candidate_id} has lower or equal concentration ({top_conc:.2f}) "
                    f"vs {second.candidate_id} ({second_conc:.2f}). Winner stays {top.candidate_id}."
                )

        trace = TieBreakTrace(
            epsilon=EPS,
            top_candidate_id=top.candidate_id,
            second_candidate_id=second.candidate_id,
            top_score=round(top_score, 3),
            second_score=round(second_score, 3),
            gap=round(gap, 3),
            triggered=gap <= EPS,
            top_concentration=round(top_conc, 3),
            second_concentration=round(second_conc, 3),
            winner_id=winner.candidate_id,
            reason=reason,
        )
        return winner, trace

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
        dissent, _ = self._detect_dissent_with_trace(winner, arguments)
        return dissent

    def _detect_dissent_with_trace(
        self,
        winner: RouteCandidate,
        arguments: List[AgentArgument],
    ) -> tuple[Optional[str], DissentTrace]:
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

        trace = DissentTrace(
            threshold=DISSENT_THRESHOLD,
            dissent_lines=dissent_lines,
            had_dissent=bool(dissent_lines),
        )
        if not dissent_lines:
            return None, trace
        return " ".join(dissent_lines), trace

    def _generate_why_not(
        self,
        surviving: List[RouteCandidate],
        winner: RouteCandidate,
        arguments: List[AgentArgument],
        aggregates: Dict[str, float],
    ) -> Dict[str, str]:
        why_not, _ = self._generate_why_not_with_trace(
            surviving, winner, arguments, aggregates
        )
        return why_not

    def _generate_why_not_with_trace(
        self,
        surviving: List[RouteCandidate],
        winner: RouteCandidate,
        arguments: List[AgentArgument],
        aggregates: Dict[str, float],
    ) -> tuple[Dict[str, str], List[WhyNotTrace]]:
        """One-line explanation for each runner-up."""
        why_not: Dict[str, str] = {}
        traces: List[WhyNotTrace] = []
        for c in surviving:
            if c.candidate_id == winner.candidate_id:
                continue
            agg_score = aggregates.get(c.candidate_id, 0.0)
            winner_score = aggregates.get(winner.candidate_id, 0.0)
            delta = winner_score - agg_score

            worst_agent_name = None
            worst_agent_score = None
            # Find the agent that most hurt this candidate
            agent_args = [a for a in arguments if a.candidate_id == c.candidate_id]
            if agent_args:
                worst_agent = min(agent_args, key=lambda a: a.score)
                reason = (
                    f"Scored {agg_score:.1f}/10 aggregate vs winner's {winner_score:.1f}. "
                    f"{worst_agent.agent_name} gave it only {worst_agent.score:.1f}/10 "
                    f"— its weakest point."
                )
                worst_agent_name = worst_agent.agent_name
                worst_agent_score = worst_agent.score
            else:
                reason = (
                    f"Scored {agg_score:.1f}/10 aggregate, {delta:.1f} points below the winner."
                )
            why_not[c.candidate_id] = reason
            traces.append(
                WhyNotTrace(
                    runner_up_id=c.candidate_id,
                    runner_up_label=c.label,
                    aggregate_score=round(agg_score, 3),
                    winner_score=round(winner_score, 3),
                    delta=round(delta, 3),
                    worst_agent=worst_agent_name,
                    worst_agent_score=round(worst_agent_score, 3) if worst_agent_score is not None else None,
                    explanation=reason,
                )
            )
        return why_not, traces

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
