"""
BudgetAgent — Phase 3 real agent.

Deterministic analysis:
    - Calls manzil.tools.cost_calc.estimate_cost(route, query) -> CostBreakdown
    - Decomposes: transport + lodging + food + activities + 10% buffer

Hard blockers:
    - Veto if total > query.budget_pkr * 1.15 (the relaxation tolerance)

Score:
    - Linear inverse of cost overshoot, capped at 10 when within budget.

LLM argument:
    - Reasons cite "fits comfortably", "transport-light"
    - Concerns cite "lodging at peak season", "guide fees not budgeted"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from manzil.agents.base import BaseAgent
from manzil.schemas import RouteCandidate, UserQuery
from manzil.tools.cost_calc import estimate_cost


class BudgetAgent(BaseAgent):
    name = "BudgetAgent"
    uses_llm = True

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        breakdown = estimate_cost(candidate, query)
        budget = int(query.budget_pkr)
        delta = breakdown.total - budget
        pct_over = (delta / budget * 100.0) if budget > 0 else 0.0
        relaxation_limit = budget * 1.15

        # Determine which tier was used for the lodging
        if getattr(query, "luxury_stays_needed", False):
            lodging_tier = "high"
        else:
            per_day = budget / max(1, query.days)
            if per_day <= 2500:
                lodging_tier = "low"
            elif per_day <= 7000:
                lodging_tier = "mid"
            else:
                lodging_tier = "high"

        return {
            "estimated_cost_pkr": breakdown.total,
            "user_budget_pkr": budget,
            "delta_pkr": delta,
            "pct_over_budget": round(pct_over, 1),
            "relaxation_limit_pkr": int(relaxation_limit),
            "within_budget": breakdown.total <= budget,
            "within_relaxation": breakdown.total <= relaxation_limit,
            "lodging_tier": lodging_tier,
            "transport": breakdown.transport,
            "lodging": breakdown.lodging,
            "food": breakdown.food,
            "activities": breakdown.activities,
            "buffer": breakdown.buffer,
            "total": breakdown.total,
            "breakdown": {
                "transport": breakdown.transport,
                "lodging": breakdown.lodging,
                "food": breakdown.food,
                "activities": breakdown.activities,
                "buffer": breakdown.buffer,
            },
        }

    def _check_blocker(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> Optional[str]:
        if not analysis.get("within_relaxation", True):
            total = analysis.get("estimated_cost_pkr", 0)
            limit = analysis.get("relaxation_limit_pkr", 0)
            return (
                f"Estimated cost PKR {total:,} exceeds the relaxation limit of "
                f"PKR {limit:,} (115% of budget)."
            )
        return None

    def _score(
        self, analysis: Dict[str, Any], candidate: RouteCandidate, query: UserQuery
    ) -> float:
        pct_over = analysis.get("pct_over_budget", 0.0)
        budget = analysis.get("user_budget_pkr", 1)
        total = analysis.get("estimated_cost_pkr", 0)

        if total <= 0 or budget <= 0:
            return 5.0

        # Linear inverse: 10 at <= budget, linearly drops to 0 at +50% over
        if pct_over <= 0:
            return 10.0
        if pct_over >= 50:
            return 0.0

        # Linear interpolation: 10 -> 0 as pct_over goes 0 -> 50
        return max(0.0, 10.0 - (pct_over / 50.0) * 10.0)

    def _build_argue_prompt(
        self,
        analysis: Dict[str, Any],
        score: float,
        candidate: RouteCandidate,
        query: UserQuery,
    ) -> str:
        bd = analysis.get("breakdown", {})
        lines = [
            f"Candidate: {candidate.label}",
            f"Destinations: {' -> '.join(candidate.destinations)}",
            f"Trip days: {candidate.days}; group size: {query.group_size}",
            f"BudgetAgent deterministic score: {score:.1f}/10",
            "",
            "Cost breakdown (PKR):",
            f"- Transport:  {bd.get('transport', 0):,}",
            f"- Lodging:    {bd.get('lodging', 0):,}",
            f"- Food:       {bd.get('food', 0):,}",
            f"- Activities: {bd.get('activities', 0):,}",
            f"- Buffer:     {bd.get('buffer', 0):,}",
            f"- TOTAL:      {analysis['estimated_cost_pkr']:,}",
            "",
            f"User budget: PKR {analysis['user_budget_pkr']:,}",
            f"Over/under budget: {analysis['delta_pkr']:,} PKR "
            f"({analysis['pct_over_budget']:.0f}%)",
            f"Within 15% relaxation: {'yes' if analysis['within_relaxation'] else 'NO'}",
            "",
            "Produce a JSON object with exactly two keys:",
            '  "reasons":  1-3 short bullets (<=25 words each) supporting this candidate',
            "              from a budget perspective.",
            '  "concerns": 1-3 short bullets (<=25 words each) flagging budget risks.',
            "",
            "Cite the data above. Do not invent costs. Reply with ONLY the JSON.",
        ]
        return "\n".join(lines)

    def _templated_reasons(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        reasons = []
        total = analysis.get("estimated_cost_pkr", 0)
        budget = analysis.get("user_budget_pkr", 1)
        delta = analysis.get("delta_pkr", 0)
        pct_over = analysis.get("pct_over_budget", 0.0)
        within = analysis.get("within_budget", False)
        bd = analysis.get("breakdown", {})
        transport = bd.get("transport", 0)
        lodging = bd.get("lodging", 0)

        if within:
            reasons.append(f"Fits comfortably within budget at PKR {total:,} (under by PKR {-delta:,}).")
        elif pct_over <= 5:
            reasons.append(f"Slightly over budget by {pct_over:.0f}% — still very manageable.")
        if transport < budget * 0.3:
            reasons.append("Transport costs are reasonable for this route length.")
        if lodging < budget * 0.4:
            reasons.append("Lodging allocation leaves room for upgrades or extras.")

        return reasons

    def _templated_concerns(
        self, analysis: Dict[str, Any], score: float, candidate: RouteCandidate, query: UserQuery
    ) -> List[str]:
        concerns = []
        pct_over = analysis.get("pct_over_budget", 0.0)
        delta = analysis.get("delta_pkr", 0)

        if pct_over > 10:
            concerns.append(f"Over budget by {pct_over:.0f}% — consider trimming activities or lodging tier.")
        if pct_over > 25:
            concerns.append("Significantly over budget — may need to drop a destination or downgrade accommodation.")
        if delta > 20000:
            concerns.append(f"Budget gap of PKR {delta:,} is substantial for this group size.")

        return concerns


__all__ = ["BudgetAgent"]
