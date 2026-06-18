"""
Replanning mechanism.

Triggered by user input or disruption events. Constructs a modified
UserQuery, re-runs the recommender and debate, and returns a new
DebateResult. The original is preserved by the caller.

Why a full re-run rather than incremental adjustment:
    - The debate is cheap (~16 LLM calls, mostly cached)
    - Small disruptions can have large consequences (a closed pass
      eliminates whole routes), so a full re-run produces more honest
      results than a patched-up original.
"""

from __future__ import annotations

from copy import deepcopy
from typing import List

from manzil.graph.debate_graph import run_debate
from manzil.recommender.pipeline import recommend
from manzil.schemas import DebateResult, Disruption, UserQuery


def replan(
    original_query: UserQuery,
    disruption: Disruption,
    original_candidates: List = None,
) -> DebateResult:
    """
    Apply a disruption to the original query and re-run the full pipeline.

    Args:
        original_query: The user's original query
        disruption: The disruption event to apply
        original_candidates: Optional; if provided and the disruption
            does not affect routing, we may short-circuit. Currently
            always does a full re-run.

    Returns:
        A new DebateResult reflecting the post-disruption recommendation.
    """
    modified = _apply_disruption(original_query, disruption)
    new_candidates = recommend(modified)
    result = run_debate(modified, new_candidates)
    return result


def _apply_disruption(query: UserQuery, disruption: Disruption) -> UserQuery:
    """
    Build a modified UserQuery based on the disruption kind.
    """
    modified = deepcopy(query)

    if disruption.kind == "road_closed":
        # Add the closed pass to hard constraints
        if disruption.pass_id:
            constraint = f"avoid_pass:{disruption.pass_id}"
            if constraint not in modified.hard_constraints:
                modified.hard_constraints.append(constraint)

    elif disruption.kind == "budget_cut":
        # Reduce budget by pct_cut percent
        if disruption.pct_cut:
            cut = disruption.pct_cut / 100.0
            modified.budget_pkr = int(modified.budget_pkr * (1 - cut))

    elif disruption.kind == "weather_event":
        # Shift dates if possible, or add weather constraint
        if disruption.day_index and disruption.destination_id:
            # For now, we add a soft constraint note; the recommender
            # does not yet interpret day-specific constraints, so we
            # rely on the debate's WeatherAgent to flag issues.
            modified.hard_constraints.append(
                f"weather_alert:{disruption.destination_id}:day{disruption.day_index}"
            )

    elif disruption.kind == "flight_cancelled":
        # Force road or hybrid mode if flight leg is cancelled
        if modified.travel_mode_pref.value == "air":
            modified.travel_mode_pref = query.travel_mode_pref.__class__("road")

    return modified


__all__ = ["replan"]
