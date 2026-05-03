"""
Recommender pipeline — Phase 2 (real).

Replaces the Phase-1 stub. The full flow is:

    filter → enumerate → score (CBR + content + hybrid) → MMR-diversity

If the strict pass yields fewer than 3 candidates, the constraint-relaxation
loop tries successively looser queries and surfaces the first relaxation
note that produced results — the recommender does NOT fail silently.

Public API is unchanged from Phase 1: `recommend(query) -> List[RouteCandidate]`.
"""

from __future__ import annotations

from typing import Dict, List

from manzil.data_loader import (
    load_case_base,
    load_costs,
    load_destinations,
)
from manzil.recommender import cbr, content, diversity, relaxation
from manzil.recommender.enumerate import EnumeratedRoute, enumerate_routes
from manzil.recommender.filter import filter_destinations
from manzil.recommender.hybrid import hybrid_score
from manzil.schemas import (
    CaseBaseEntry,
    Destination,
    RouteCandidate,
    TravelMode,
    UserQuery,
)


def recommend(query: UserQuery) -> List[RouteCandidate]:
    """
    Return exactly 3 diverse candidate routes, or fewer if even the relaxed
    pipeline produces nothing. Each candidate carries `diversity_axes` tags
    and a rationale string. Relaxed runs add a note to the rationale.
    """
    destinations = load_destinations()
    case_base = load_case_base()

    # Strict pass
    strict = _try_recommend(query, destinations, case_base)
    if len(strict) >= 3:
        return strict

    # Relaxation passes — yield successively looser queries
    for step in relaxation.relax(query):
        relaxed = _try_recommend(step.query, destinations, case_base)
        if len(relaxed) >= 3:
            for cand in relaxed:
                cand.rationale = f"⚠ {step.note}\n\n{cand.rationale}"
            return relaxed
        if relaxed and len(relaxed) > len(strict):
            strict = relaxed
            for cand in strict:
                cand.rationale = f"⚠ {step.note}\n\n{cand.rationale}"

    return strict


# ---------------------------------------------------------------------------
# Strict-pass implementation (used for both the strict run and each
# relaxation step)
# ---------------------------------------------------------------------------


def _try_recommend(
    query: UserQuery,
    destinations: Dict[str, Destination],
    case_base: List[CaseBaseEntry],
) -> List[RouteCandidate]:
    fr = filter_destinations(query, destinations)
    if not fr.feasible:
        return []

    routes = enumerate_routes(list(fr.feasible.keys()))
    if not routes:
        return []

    scored: List[RouteCandidate] = []
    for i, r in enumerate(routes):
        cbr_s = cbr.score_route(r.destinations, query, case_base)
        content_s = content.score_route(r.destinations, query, destinations)
        cost = _estimate_cost(r, query, destinations)
        axes = diversity.compute_axes(r.destinations, query, destinations, cost)
        scored.append(
            RouteCandidate(
                candidate_id=f"cand-{i}",
                label=_label_for(r.destinations, axes, destinations),
                destinations=r.destinations,
                travel_modes=_modes_for(r, query),
                estimated_cost=cost,
                days=query.days,
                diversity_axes=axes,
                cbr_score=cbr_s,
                content_score=content_s,
                rationale=_rationale_for(cbr_s, content_s, axes, case_base),
            )
        )

    picked = diversity.pick_diverse_three(scored)
    # Reassign clean A/B/C ids for the UI
    for letter, cand in zip("ABC", picked):
        cand.candidate_id = f"cand-{letter}"
    return picked


# ---------------------------------------------------------------------------
# Cost estimate (used for diversity-axis tagging; Phase 3 BudgetAgent does
# the proper decomposition for the debate scoring)
# ---------------------------------------------------------------------------


def _season_bucket(travel_month: int) -> str:
    if travel_month in (6, 7, 8):
        return "high"
    if travel_month in (4, 5, 9, 10):
        return "shoulder"
    return "low"


def _tier_for_budget(budget_pkr: int, group_size: int, days: int) -> str:
    """A loose budget→tier mapping for the cost lookup table."""
    if days < 1:
        return "low"
    per_person_per_day = budget_pkr / max(1, group_size) / max(1, days)
    if per_person_per_day < 6_000:
        return "low"
    if per_person_per_day < 14_000:
        return "mid"
    return "high"


def _estimate_cost(
    route: EnumeratedRoute,
    query: UserQuery,
    destinations: Dict[str, Destination],
) -> int:
    if not route.destinations:
        return 0
    costs = load_costs()
    season = _season_bucket(query.travel_month)
    tier = _tier_for_budget(query.budget_pkr, query.group_size, query.days)

    # Lodging — region-specific table when available, else destination's
    # cost_per_day field.
    lodging_per_night_per_person = 0
    days_per_dest = max(1, query.days // len(route.destinations))
    for dest_id in route.destinations:
        dest = destinations.get(dest_id)
        if dest is None:
            continue
        region_key = _region_key(dest.region)
        region_table = costs.get("lodging_per_night", {}).get(region_key, {})
        season_table = region_table.get(season, {})
        if tier in season_table:
            lodging_per_night_per_person += int(season_table[tier])
        else:
            lodging_per_night_per_person += int(dest.cost_per_day.get("mid", 7000))
    avg_lodging = lodging_per_night_per_person / max(1, len(route.destinations))
    lodging_total = int(avg_lodging * days_per_dest * len(route.destinations) * query.group_size)

    # Food + activities (per-person-per-day)
    food = costs.get("food_per_person_per_day", {}).get(tier, 1800)
    acts = costs.get("activities_per_day", {}).get(tier, 1500)
    food_acts = int((food + acts) * query.days * query.group_size)

    # Transport — origin → first stop, plus per-segment intra-route
    transport = _transport_cost(
        query.origin_city, route.destinations[0], query.travel_mode_pref
    )
    transport *= query.group_size
    # Add a flat 1500 PKR per intra-leg per person for fuel/local transport
    transport += int(1500 * max(0, len(route.destinations) - 1) * query.group_size)

    buffer_pct = float(costs.get("buffer_pct", 0.10))
    subtotal = lodging_total + food_acts + transport
    return subtotal + int(subtotal * buffer_pct)


_REGION_MAP = {
    "Gilgit-Baltistan": "gilgit-baltistan",
    "Khyber Pakhtunkhwa": "khyber-pakhtunkhwa",
    "Punjab": "punjab",
    "Azad Kashmir": "khyber-pakhtunkhwa",  # closest match in our cost table
}


def _region_key(region: str) -> str:
    return _REGION_MAP.get(region, "gilgit-baltistan")


def _transport_cost(origin: str, dest: str, mode: TravelMode) -> int:
    costs = load_costs()
    table = (
        costs.get("transport", {})
        .get(origin.lower(), {})
        .get(dest, {})
    )
    return int(table.get(mode.value, table.get("road", 10_000)))


# ---------------------------------------------------------------------------
# Travel modes — one entry per inter-stop segment
# ---------------------------------------------------------------------------


def _modes_for(route: EnumeratedRoute, query: UserQuery) -> List[TravelMode]:
    # In Phase 2 we tile the user's preference across all segments. Phase 3
    # could vary per-segment based on what's actually feasible.
    return [query.travel_mode_pref] * max(1, len(route.destinations))


# ---------------------------------------------------------------------------
# Cosmetic helpers — label and rationale strings for the UI
# ---------------------------------------------------------------------------


_BUDGET_POSTURE_LABEL = {
    "at-budget": "within budget",
    "near-budget": "close to budget",
    "budget-stretch": "budget-stretch",
}


def _label_for(
    route: List[str],
    axes: Dict[str, str],
    destinations: Dict[str, Destination],
) -> str:
    if not route:
        return "(empty route)"
    names = [destinations[d].name.split(",")[0] for d in route if d in destinations]
    body = " + ".join(names) if len(names) <= 3 else f"{names[0]} + {len(names)-1} more"
    posture = _BUDGET_POSTURE_LABEL.get(axes.get("budget_posture", ""), "")
    pace = axes.get("pace", "")
    suffix_bits = [b for b in (pace, posture) if b]
    suffix = f" ({', '.join(suffix_bits)})" if suffix_bits else ""
    return body + suffix


def _rationale_for(
    cbr_s: float,
    content_s: float,
    axes: Dict[str, str],
    case_base: List[CaseBaseEntry],
) -> str:
    h = hybrid_score(cbr_s, content_s)
    bits = [
        f"Hybrid fit score {h:.2f} (CBR {cbr_s:.2f} · style {content_s:.2f}).",
        f"Profile: {axes.get('scope', '?')}, {axes.get('pace', '?')} pace, "
        f"{axes.get('risk', '?')} risk.",
    ]
    if cbr_s > 0.6 and case_base:
        bits.append(
            f"Similar travellers in our case base "
            f"({len(case_base)} cases) rated routes like this highly."
        )
    return " ".join(bits)


__all__ = ["recommend"]
