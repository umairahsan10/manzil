"""
Recommender pipeline.

**Phase 1 — STUB.** Returns 3 hand-crafted candidates that differ along the
section-4 diversity axes (scope / mode-mix / pace / risk / budget posture).
The Phase-2 implementation replaces this with the real
constraint-filter → CBR → content → relaxation → MMR-diversity pipeline,
behind the same `recommend(query) -> List[RouteCandidate]` signature.

The stub deliberately ignores most of `query` — it returns the same 3
skeletons regardless of style/budget/origin — but it scales the cost
estimate roughly to days × group_size × tier so the Budget Agent has
something to argue about.
"""

from __future__ import annotations

from typing import List

from manzil.schemas import RouteCandidate, TravelMode, UserQuery


def recommend(query: UserQuery) -> List[RouteCandidate]:
    """Return exactly 3 diverse candidate routes."""
    days = query.days
    group = query.group_size

    cand_a = RouteCandidate(
        candidate_id="cand-A",
        label="Safe default — Hunza only, road",
        destinations=["hunza-karimabad"],
        travel_modes=[TravelMode.ROAD],
        estimated_cost=max(70_000, days * group * 5_000),
        days=days,
        diversity_axes={
            "scope": "single-region",
            "mode_mix": "all-road",
            "pace": "relaxed",
            "risk": "conservative",
            "budget_posture": "at-budget",
        },
        cbr_score=0.0,
        content_score=0.0,
        rationale=(
            "Single base in Karimabad; minimal transit; plenty of time per stop. "
            "Lowest-risk option — same valley for the whole trip."
        ),
    )

    cand_b = RouteCandidate(
        candidate_id="cand-B",
        label="Value pick — Naran + Hunza, road",
        destinations=["naran", "hunza-karimabad"],
        travel_modes=[TravelMode.ROAD, TravelMode.ROAD],
        estimated_cost=max(95_000, days * group * 6_500),
        days=days,
        diversity_axes={
            "scope": "multi-region",
            "mode_mix": "all-road",
            "pace": "moderate",
            "risk": "moderate",
            "budget_posture": "at-budget",
        },
        cbr_score=0.0,
        content_score=0.0,
        rationale=(
            "Two valleys on the same KKH spine — Naran first to acclimatize, "
            "Hunza second for the cultural payoff."
        ),
    )

    cand_c = RouteCandidate(
        candidate_id="cand-C",
        label="Ambitious — Skardu + Hunza + Fairy Meadows, fly-and-road",
        destinations=["skardu", "hunza-karimabad", "fairy-meadows"],
        travel_modes=[TravelMode.AIR, TravelMode.ROAD, TravelMode.ROAD],
        estimated_cost=max(140_000, days * group * 9_000),
        days=days,
        diversity_axes={
            "scope": "multi-region",
            "mode_mix": "fly-and-road",
            "pace": "packed",
            "risk": "ambitious",
            "budget_posture": "budget-stretch",
        },
        cbr_score=0.0,
        content_score=0.0,
        rationale=(
            "Fly into Skardu to save 30+ hours of road; loop back via Hunza and "
            "Fairy Meadows by KKH. Three distinct regions in one trip."
        ),
    )

    return [cand_a, cand_b, cand_c]


__all__ = ["recommend"]
