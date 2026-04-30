"""
BudgetAgent — Phase 1 stub.

Deterministic only. Compares the candidate's `estimated_cost` to the
user's `budget_pkr`. No LLM. No vetoes in Phase 1 (Phase 3 vetoes when
over budget by more than 15%, the relaxation tolerance).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from manzil.agents.base import BaseAgent
from manzil.schemas import LLMArgumentPayload, RouteCandidate, UserQuery


class BudgetAgent(BaseAgent):
    name = "BudgetAgent"
    uses_llm = False

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        cost = int(candidate.estimated_cost)
        budget = int(query.budget_pkr)
        delta = cost - budget
        pct_over = (delta / budget * 100.0) if budget > 0 else 0.0
        return {
            "estimated_cost_pkr": cost,
            "user_budget_pkr": budget,
            "delta_pkr": delta,
            "pct_over_budget": round(pct_over, 1),
        }

    def _check_blocker(self, analysis, candidate, query) -> Optional[str]:
        return None  # Phase 3 vetoes at >15% over

    def _score(self, analysis, candidate, query) -> float:
        pct_over = analysis.get("pct_over_budget", 0.0)
        if pct_over <= -10:
            return 10.0  # well under budget
        if pct_over <= 0:
            return 9.0
        if pct_over <= 10:
            return 7.0
        if pct_over <= 25:
            return 4.0
        return 1.0

    def _canned_argument(
        self, analysis, score, candidate, query
    ) -> LLMArgumentPayload:
        pct = analysis.get("pct_over_budget", 0.0)
        cost = analysis.get("estimated_cost_pkr", 0)
        budget = analysis.get("user_budget_pkr", 0)

        reasons = []
        concerns = []
        if pct <= 0:
            reasons.append(
                f"Estimated PKR {cost:,} fits the PKR {budget:,} budget "
                f"({pct:.0f}%)."
            )
        elif pct <= 10:
            reasons.append(
                f"Estimated PKR {cost:,} is close to the PKR {budget:,} budget "
                f"({pct:.0f}% over) — manageable with small adjustments."
            )
        else:
            concerns.append(
                f"Estimated PKR {cost:,} is {pct:.0f}% over the PKR {budget:,} budget; "
                f"trip will need a meaningful budget bump."
            )

        if pct >= 5:
            concerns.append(
                "High-season lodging and transport surcharges not yet itemized."
            )

        if not reasons and not concerns:
            reasons.append("Cost profile is within typical bounds for this region.")

        return LLMArgumentPayload(reasons=reasons[:3], concerns=concerns[:3])


__all__ = ["BudgetAgent"]
