"""
LocalExperienceAgent — Phase 1 stub.

Deterministic only. Scores by overlap between the user's `style_tags`
and the destinations' `activity_tags`. No RAG. No LLM. Never blocks.

Phase 3 promotes this to a RAG-grounded agent over `data/local_corpus/`
with refusal on empty retrieval.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from manzil.agents.base import BaseAgent
from manzil.data_loader import load_destinations
from manzil.schemas import LLMArgumentPayload, RouteCandidate, UserQuery


class LocalExperienceAgent(BaseAgent):
    name = "LocalExperienceAgent"
    uses_llm = False

    def _analyze(
        self, candidate: RouteCandidate, query: UserQuery
    ) -> Dict[str, Any]:
        destinations_by_id = load_destinations()
        user_styles = {s.lower() for s in query.style_tags}

        per_dest = []
        all_overlap = set()
        for dest_id in candidate.destinations:
            dest = destinations_by_id.get(dest_id)
            if dest is None:
                per_dest.append({"id": dest_id, "matched_tags": []})
                continue
            tags = {t.lower() for t in dest.activity_tags}
            overlap = sorted(tags & user_styles)
            all_overlap.update(overlap)
            per_dest.append(
                {
                    "id": dest_id,
                    "name": dest.name,
                    "all_tags": sorted(tags),
                    "matched_tags": overlap,
                }
            )

        return {
            "user_style_tags": sorted(user_styles),
            "per_destination": per_dest,
            "aggregate_match_count": len(all_overlap),
            "aggregate_matched_tags": sorted(all_overlap),
        }

    def _check_blocker(self, analysis, candidate, query) -> Optional[str]:
        return None  # Local experience never blocks (Readme §6)

    def _score(self, analysis, candidate, query) -> float:
        per_dest = analysis.get("per_destination", [])
        if not per_dest:
            return 5.0
        total_matches = sum(len(d.get("matched_tags", [])) for d in per_dest)
        avg = total_matches / len(per_dest)
        # Map: 0 matches → 4.0, 1 match → 6.0, 2 → 8.0, 3+ → 10.0
        return min(10.0, 4.0 + 2.0 * avg)

    def _canned_argument(
        self, analysis, score, candidate, query
    ) -> LLMArgumentPayload:
        matched = analysis.get("aggregate_matched_tags", [])
        per_dest = analysis.get("per_destination", [])

        reasons = []
        concerns = []
        if matched:
            reasons.append(
                "Route activity profile aligns with your styles: "
                + ", ".join(matched[:4])
                + "."
            )
        else:
            concerns.append(
                "No direct overlap between your style tags and the destinations' "
                "activity profile — the trip may feel less personalized."
            )

        if len(per_dest) >= 3:
            concerns.append(
                "Three+ destinations means less time at each — pick favourites."
            )
        elif len(per_dest) == 1:
            reasons.append(
                "Single base — easier to find genuine local experiences than a hopping itinerary."
            )

        if not reasons and not concerns:
            reasons.append("Standard mix of local experiences available for this route.")

        return LLMArgumentPayload(reasons=reasons[:3], concerns=concerns[:3])


__all__ = ["LocalExperienceAgent"]
