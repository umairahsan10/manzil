"""
Diversity selection (greedy MMR) — Phase 2.

Given a list of scored `RouteCandidate`s, pick 3 that span the 5 diversity
axes meaningfully. Without this step the recommender tends to return three
top-ranked-but-similar candidates and the downstream multi-agent debate
collapses into "they're all kind of the same".

Greedy MMR (Maximal Marginal Relevance):

    1. Pick the candidate with the highest hybrid score.
    2. For each remaining candidate, compute
           mmr(c) = hybrid_score(c) - lambda * max_similarity(c, already_picked)
       Pick the candidate with the highest mmr.
    3. Repeat until 3 are picked.

Similarity is the fraction of the 5 axes that match exactly.
Default `lambda = 0.5`.
"""

from __future__ import annotations

from typing import Dict, List

from manzil.schemas import (
    Destination,
    DiversityTrace,
    MMRStep,
    RouteCandidate,
    TravelMode,
    UserQuery,
)

DEFAULT_LAMBDA = 0.5
DEFAULT_ALPHA = 0.6  # hybrid blend; same default as hybrid.py

AXES = ("scope", "mode_mix", "pace", "risk", "budget_posture")


# ---------------------------------------------------------------------------
# Diversity-axis computation
# ---------------------------------------------------------------------------


def compute_axes(
    route: List[str],
    query: UserQuery,
    destinations: Dict[str, Destination],
    estimated_cost: int,
) -> Dict[str, str]:
    """Tag a route with values along each of the 5 diversity axes."""

    # scope: single- vs multi-region
    regions = {destinations[d].region for d in route if d in destinations}
    scope = "single-region" if len(regions) <= 1 else "multi-region"

    # mode_mix: derived from travel-mode preference + which destinations the
    # route includes (a hybrid query through Skardu/Gilgit/Chitral implies
    # fly-and-road; pure-road query is all-road; air-pref is fly-heavy).
    flight_served = {"skardu", "gilgit", "chitral"}
    if query.travel_mode_pref == TravelMode.AIR:
        mode_mix = "fly-heavy"
    elif query.travel_mode_pref == TravelMode.HYBRID and any(
        d in flight_served for d in route
    ):
        mode_mix = "fly-and-road"
    else:
        mode_mix = "all-road"

    # pace: stops per day
    pace_ratio = len(route) / max(1, query.days)
    if pace_ratio < 0.3:
        pace = "relaxed"
    elif pace_ratio < 0.5:
        pace = "moderate"
    else:
        pace = "packed"

    # risk: max altitude on route
    max_alt = max((destinations[d].altitude_m for d in route if d in destinations), default=0)
    if max_alt < 2500:
        risk = "conservative"
    elif max_alt < 3500:
        risk = "moderate"
    else:
        risk = "ambitious"

    # budget_posture
    if estimated_cost <= query.budget_pkr:
        budget_posture = "at-budget"
    elif estimated_cost <= int(query.budget_pkr * 1.10):
        budget_posture = "near-budget"
    else:
        budget_posture = "budget-stretch"

    return {
        "scope": scope,
        "mode_mix": mode_mix,
        "pace": pace,
        "risk": risk,
        "budget_posture": budget_posture,
    }


# ---------------------------------------------------------------------------
# MMR selection
# ---------------------------------------------------------------------------


def _hybrid(c: RouteCandidate, alpha: float) -> float:
    return alpha * c.cbr_score + (1.0 - alpha) * c.content_score


def _axis_similarity(a: RouteCandidate, b: RouteCandidate) -> float:
    if not a.diversity_axes or not b.diversity_axes:
        return 0.0
    matches = sum(
        1 for axis in AXES if a.diversity_axes.get(axis) == b.diversity_axes.get(axis)
    )
    return matches / len(AXES)


def pick_diverse_three(
    candidates: List[RouteCandidate],
    *,
    alpha: float = DEFAULT_ALPHA,
    lambda_: float = DEFAULT_LAMBDA,
    return_trace: bool = False,
) -> List[RouteCandidate] | tuple[List[RouteCandidate], list[MMRStep]]:
    """Return the 3 most-diverse-but-still-good candidates.

    We run MMR even when `len(candidates) <= 3` because the ORDER matters
    (the second slot should be the most-diverse-relative-to-the-winner,
    not the second-highest scorer).
    """
    if len(candidates) <= 1:
        if return_trace:
            return list(candidates), []
        return list(candidates)

    pool = list(candidates)
    # 1. Top-1 by hybrid score
    pool.sort(key=lambda c: -_hybrid(c, alpha))
    picked: List[RouteCandidate] = [pool.pop(0)]
    mmr_steps: list[MMRStep] = [
        MMRStep(
            step=1,
            candidate_id=picked[0].candidate_id,
            candidate_label=picked[0].label,
            hybrid_score=round(_hybrid(picked[0], alpha), 3),
            max_axis_similarity_to_picked=0.0,
            mmr_score=round(_hybrid(picked[0], alpha), 3),
            lambda_=lambda_,
            picked_so_far=[picked[0].candidate_id],
        )
    ]

    # 2-3. Greedy MMR for remaining slots
    while len(picked) < 3 and pool:
        best_idx = 0
        best_mmr = -1e9
        best_sim = 0.0
        for i, c in enumerate(pool):
            sim = max(_axis_similarity(c, p) for p in picked)
            mmr = _hybrid(c, alpha) - lambda_ * sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i
                best_sim = sim
        chosen = pool.pop(best_idx)
        picked.append(chosen)
        mmr_steps.append(
            MMRStep(
                step=len(picked),
                candidate_id=chosen.candidate_id,
                candidate_label=chosen.label,
                hybrid_score=round(_hybrid(chosen, alpha), 3),
                max_axis_similarity_to_picked=round(best_sim, 3),
                mmr_score=round(best_mmr, 3),
                lambda_=lambda_,
                picked_so_far=[p.candidate_id for p in picked],
            )
        )

    if return_trace:
        return picked, mmr_steps
    return picked


__all__ = ["AXES", "compute_axes", "pick_diverse_three", "DEFAULT_LAMBDA", "DEFAULT_ALPHA"]
