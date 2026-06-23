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

from manzil.data_loader import load_destinations, load_safety_knowledge
from manzil.llm import Model
from manzil.schemas import (
    AgentArgument,
    AgentScoreDetail,
    AltitudePoint,
    CandidateAggregate,
    CostBreakdownDetailed,
    DayByDayPlan,
    DayPlan,
    DayStop,
    DayWeatherCard,
    DebateResult,
    DebateTrace,
    DissentTrace,
    ExperienceLayer,
    ExperienceSpot,
    FacilityProximity,
    OrchestratorTrace,
    RoadRiskCard,
    RouteCandidate,
    SafetyAnalysis,
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
        safety_analysis = self._build_safety_analysis(winner, arguments)
        experience_layer = self._build_experience_layer(winner, arguments)
        cost_breakdown = self._build_cost_breakdown(winner, arguments)

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
            safety_analysis=safety_analysis,
            experience_layer=experience_layer,
            cost_breakdown=cost_breakdown,
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

        # Extract per-destination structured data from agent raw_data
        weather_by_dest = self._weather_data_by_dest(arguments, winner.candidate_id)
        road_risk_by_dest = self._road_risk_by_dest(arguments, winner.candidate_id)
        safety_raw = self._agent_raw(arguments, "SafetyAgent", winner.candidate_id)
        budget_raw = self._agent_raw(arguments, "BudgetAgent", winner.candidate_id)
        stay_tier = "high" if budget_raw and budget_raw.get("lodging_tier") == "high" else "mid"

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
                # Weather card from agent raw_data
                w_data = weather_by_dest.get(dest_id, {})
                weather_card = None
                if w_data and not w_data.get("error"):
                    weather_card = DayWeatherCard(
                        destination_id=dest_id,
                        temp_high_c=w_data.get("avg_high_c"),
                        temp_low_c=w_data.get("avg_low_c"),
                        precip_prob_pct=w_data.get("peak_precip_prob_pct"),
                        precip_mm=w_data.get("total_precip_mm"),
                        summary=w_data.get("summary", ""),
                        condition=self._weather_condition(w_data),
                    )
                # Road risk card from road agent raw_data
                road_card = road_risk_by_dest.get(dest_id)

                day = DayPlan(
                    day_index=day_index,
                    stops=[stop],
                    travel_mode=travel_mode if day_index == 1 or j == 0 else None,
                    drive_time_hours=None,
                    estimated_cost=int(winner.estimated_cost / max(1, winner.days)),
                    weather_note=self._note_for(arguments, "WeatherAgent", winner.candidate_id),
                    road_note=self._note_for(arguments, "RoadAgent", winner.candidate_id),
                    safety_note=self._note_for(arguments, "SafetyAgent", winner.candidate_id),
                    stay_type=self._stay_type_for(stay_tier, dest, day_index, winner.days),
                    altitude_m=dest.altitude_m if dest else None,
                    weather=weather_card,
                    road_risk=road_card,
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

    # ------------------------------------------------------------------
    # Structured-layer builders — extract from agent raw_data
    # ------------------------------------------------------------------

    @staticmethod
    def _agent_raw(
        arguments: List[AgentArgument], agent_name: str, candidate_id: str
    ) -> Optional[dict]:
        for arg in arguments:
            if arg.agent_name == agent_name and arg.candidate_id == candidate_id:
                return arg.raw_data if isinstance(arg.raw_data, dict) else {}
        return None

    @staticmethod
    def _weather_data_by_dest(arguments: List[AgentArgument], candidate_id: str) -> dict:
        raw = Orchestrator._agent_raw(arguments, "WeatherAgent", candidate_id)
        if not raw:
            return {}
        return raw.get("per_destination", {}) if isinstance(raw.get("per_destination"), dict) else {}

    @staticmethod
    def _road_risk_by_dest(arguments: List[AgentArgument], candidate_id: str) -> dict:
        raw = Orchestrator._agent_raw(arguments, "RoadAgent", candidate_id)
        if not raw:
            return {}
        per_dest = raw.get("per_destination", [])
        out = {}
        if isinstance(per_dest, list):
            for seg in per_dest:
                if isinstance(seg, dict):
                    dest_id = seg.get("destination_id") or seg.get("id", "")
                    risk = seg.get("risk_level", "low")
                    reasons = seg.get("risk_reasons", [])
                    if dest_id:
                        out[dest_id] = RoadRiskCard(
                            segment=seg.get("segment", ""),
                            risk_level=risk,
                            reasons=reasons if isinstance(reasons, list) else [],
                        )
        return out

    @staticmethod
    def _weather_condition(w_data: dict) -> str:
        precip = w_data.get("peak_precip_prob_pct", 0) or 0
        if precip >= 70:
            return "Poor"
        if precip >= 40:
            return "Fair"
        if precip >= 20:
            return "Good"
        return "Excellent"

    @staticmethod
    def _stay_type_for(tier: str, dest, day_index: int, total_days: int) -> str:
        if dest is None:
            return "Hotel"
        if tier == "high":
            return "Hotel"
        # Mid/low tier: vary by destination type
        tags = getattr(dest, "terrain_tags", [])
        if "alpine" in tags or "meadow" in tags:
            return "Camping" if tier == "low" else "Lodge"
        return "Guesthouse" if tier == "low" else "Hotel"

    def _build_safety_analysis(
        self, winner: RouteCandidate, arguments: List[AgentArgument]
    ) -> SafetyAnalysis:
        destinations_by_id = load_destinations()
        safety_raw = self._agent_raw(arguments, "SafetyAgent", winner.candidate_id)

        altitude_points: List[AltitudePoint] = []
        hospitals: List[FacilityProximity] = []
        police: List[FacilityProximity] = []
        road_risks: List[RoadRiskCard] = []
        max_alt = 0
        threshold_m = 0
        threshold_label = ""

        # Altitude progression from destinations
        day = 1
        for dest_id in winner.destinations:
            dest = destinations_by_id.get(dest_id)
            if dest:
                altitude_points.append(
                    AltitudePoint(
                        day=day,
                        destination_id=dest_id,
                        destination_name=dest.name,
                        altitude_m=dest.altitude_m,
                    )
                )
                if dest.altitude_m > max_alt:
                    max_alt = dest.altitude_m
                day += 1

        # Hospital/police from safety agent raw_data
        if safety_raw:
            threshold_m = safety_raw.get("applied_threshold_m", 0)
            threshold_label = safety_raw.get("applied_threshold_key", "")
            per_dest = safety_raw.get("per_destination", [])
            if isinstance(per_dest, list):
                for d in per_dest:
                    if not isinstance(d, dict):
                        continue
                    dest_id = d.get("id", "")
                    hosp_name = d.get("hospital_name", "unknown")
                    hosp_dist = d.get("hospital_distance_km", 0)
                    if hosp_name and hosp_name != "unknown":
                        hospitals.append(
                            FacilityProximity(
                                destination_id=dest_id,
                                name=hosp_name,
                                distance_km=hosp_dist,
                                level=d.get("hospital_level", ""),
                            )
                        )
                    police_name = d.get("police_name", "unknown")
                    police_dist = d.get("police_distance_km", 0)
                    if police_name and police_name != "unknown":
                        police.append(
                            FacilityProximity(
                                destination_id=dest_id,
                                name=police_name,
                                distance_km=police_dist,
                            )
                        )

        # Road risk cards from road agent
        road_raw = self._agent_raw(arguments, "RoadAgent", winner.candidate_id)
        if road_raw:
            per_dest = road_raw.get("per_destination", [])
            if isinstance(per_dest, list):
                for seg in per_dest:
                    if isinstance(seg, dict):
                        road_risks.append(
                            RoadRiskCard(
                                segment=seg.get("segment", seg.get("id", "")),
                                risk_level=seg.get("risk_level", "low"),
                                reasons=seg.get("risk_reasons", []) if isinstance(seg.get("risk_reasons"), list) else [],
                            )
                        )

        # Generic emergency contacts
        emergency_contacts = [
            {"label": "Emergency Services", "number": "15"},
            {"label": "Rescue 1122", "number": "1122"},
            {"label": "Edhi Foundation", "number": "115"},
        ]

        return SafetyAnalysis(
            altitude_progression=altitude_points,
            road_risk_cards=road_risks,
            hospital_proximity=hospitals,
            police_stations=police,
            emergency_contacts=emergency_contacts,
            max_altitude_m=max_alt,
            applied_threshold_m=threshold_m,
            threshold_label=threshold_label,
        )

    def _build_experience_layer(
        self, winner: RouteCandidate, arguments: List[AgentArgument]
    ) -> ExperienceLayer:
        local_raw = self._agent_raw(arguments, "LocalAgent", winner.candidate_id)
        hidden_spots: List[ExperienceSpot] = []
        local_foods: List[ExperienceSpot] = []
        sunrise_points: List[ExperienceSpot] = []
        photo_spots: List[ExperienceSpot] = []

        if local_raw:
            per_dest = local_raw.get("per_destination", [])
            if isinstance(per_dest, list):
                for d in per_dest:
                    if not isinstance(d, dict):
                        continue
                    dest_id = d.get("id", "")
                    chunks = d.get("chunks", [])
                    if not isinstance(chunks, list):
                        continue
                    for chunk in chunks:
                        if not isinstance(chunk, dict):
                            continue
                        text = chunk.get("text", "")
                        source = chunk.get("source", "")
                        lower = text.lower()
                        # Classify chunk by keyword heuristics
                        if any(kw in lower for kw in ["food", "eat", "restaurant", "cuisine", "dish"]):
                            local_foods.append(
                                ExperienceSpot(
                                    name=text[:60].split(".")[0].strip() or "Local food",
                                    destination_id=dest_id,
                                    category="local_food",
                                    description=text[:200],
                                    source=source,
                                )
                            )
                        elif any(kw in lower for kw in ["sunrise", "sunset", "dawn", "dusk", "golden hour"]):
                            sunrise_points.append(
                                ExperienceSpot(
                                    name=text[:60].split(".")[0].strip() or "Sunrise point",
                                    destination_id=dest_id,
                                    category="sunrise_point",
                                    description=text[:200],
                                    source=source,
                                )
                            )
                        elif any(kw in lower for kw in ["photo", "viewpoint", "view point", "camera", "scenic", "overlook"]):
                            photo_spots.append(
                                ExperienceSpot(
                                    name=text[:60].split(".")[0].strip() or "Photo spot",
                                    destination_id=dest_id,
                                    category="photo_spot",
                                    description=text[:200],
                                    source=source,
                                )
                            )
                        else:
                            hidden_spots.append(
                                ExperienceSpot(
                                    name=text[:60].split(".")[0].strip() or "Hidden spot",
                                    destination_id=dest_id,
                                    category="hidden_spot",
                                    description=text[:200],
                                    source=source,
                                )
                            )

        return ExperienceLayer(
            hidden_spots=hidden_spots[:10],
            local_foods=local_foods[:10],
            sunrise_points=sunrise_points[:5],
            photo_spots=photo_spots[:10],
        )

    def _build_cost_breakdown(
        self, winner: RouteCandidate, arguments: List[AgentArgument]
    ) -> CostBreakdownDetailed:
        budget_raw = self._agent_raw(arguments, "BudgetAgent", winner.candidate_id)
        if budget_raw:
            return CostBreakdownDetailed(
                transport=budget_raw.get("transport", 0),
                lodging=budget_raw.get("lodging", 0),
                food=budget_raw.get("food", 0),
                activities=budget_raw.get("activities", 0),
                buffer=budget_raw.get("buffer", 0),
                total=budget_raw.get("total", winner.estimated_cost),
            )
        # Fallback: even split
        per_day = int(winner.estimated_cost / max(1, winner.days))
        return CostBreakdownDetailed(
            transport=int(per_day * 0.35),
            lodging=int(per_day * 0.30),
            food=int(per_day * 0.15),
            activities=int(per_day * 0.10),
            buffer=int(per_day * 0.10),
            total=winner.estimated_cost,
        )


__all__ = ["Orchestrator", "DEFAULT_WEIGHTS"]
