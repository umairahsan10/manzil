"""
Case-based reasoning — Phase 2.

For a given candidate route, find the k most-similar past cases (by user
query) and compute a rating-weighted average among those cases whose
`chosen_route` *overlaps* with the candidate.

The intuition: if travellers very similar to you went to a similar set of
places and rated it highly, that's evidence the candidate is a good fit —
even before any agent has weighed in.

Output is in [0.0, 1.0]:
    1.0 = many similar travellers visited a very similar destination set
          and rated it 5.0
    0.0 = no similar past traveller went anywhere near these destinations
"""

from __future__ import annotations

from typing import List, Tuple

from manzil.schemas import CBRTopKCase, CBRTrace, CaseBaseEntry, UserQuery

# ---------------------------------------------------------------------------
# Per-attribute similarity components (each returns [0, 1])
# ---------------------------------------------------------------------------


def _numeric_sim(a: float, b: float, scale: float) -> float:
    """1.0 when a==b; degrades linearly until |diff|>=scale, then 0."""
    return max(0.0, 1.0 - abs(a - b) / max(1e-9, scale))


def _cyclic_month_sim(a: int, b: int) -> float:
    """Months are cyclic: jan(1) and dec(12) are 1 apart, not 11."""
    diff = abs(a - b)
    cyclic = min(diff, 12 - diff)
    return 1.0 - cyclic / 6.0


def _categorical_sim(a, b) -> float:
    return 1.0 if a == b else 0.0


def _set_sim(a: List[str], b: List[str]) -> float:
    """Jaccard over the lower-cased sets."""
    sa = {x.lower() for x in a}
    sb = {x.lower() for x in b}
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


# ---------------------------------------------------------------------------
# Query similarity (weighted sum of components)
# ---------------------------------------------------------------------------

# Sum of weights = 1.0
_WEIGHTS = {
    "budget":      0.20,
    "style":       0.20,
    "month":       0.15,
    "days":        0.15,
    "difficulty":  0.10,
    "group_size":  0.05,
    "group_comp":  0.05,
    "mode":        0.05,
    "origin":      0.05,
}


def query_similarity(a: UserQuery, b: UserQuery) -> float:
    components = {
        "budget":      _numeric_sim(a.budget_pkr, b.budget_pkr, scale=200_000),
        "style":       _set_sim(a.style_tags, b.style_tags),
        "month":       _cyclic_month_sim(a.travel_month, b.travel_month),
        "days":        _numeric_sim(a.days, b.days, scale=10),
        "difficulty":  _numeric_sim(a.difficulty_tolerance, b.difficulty_tolerance, scale=4),
        "group_size":  _numeric_sim(a.group_size, b.group_size, scale=8),
        "group_comp":  _categorical_sim(a.group_composition, b.group_composition),
        "mode":        _categorical_sim(a.travel_mode_pref, b.travel_mode_pref),
        "origin":      _categorical_sim(a.origin_city.lower(), b.origin_city.lower()),
    }
    return sum(_WEIGHTS[k] * v for k, v in components.items())


# ---------------------------------------------------------------------------
# Route similarity (Jaccard on destination sets)
# ---------------------------------------------------------------------------


def route_overlap(route_a: List[str], route_b: List[str]) -> float:
    sa, sb = set(route_a), set(route_b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


# ---------------------------------------------------------------------------
# Score one route against the case base
# ---------------------------------------------------------------------------


def score_route(
    route: List[str],
    query: UserQuery,
    case_base: List[CaseBaseEntry],
    *,
    k: int = 10,
    return_trace: bool = False,
) -> float | Tuple[float, CBRTrace]:
    """
    Returns a CBR score in [0.0, 1.0] for the route under this query.
    If return_trace=True, returns (score, CBRTrace).
    """
    if not case_base or not route:
        if return_trace:
            return 0.0, CBRTrace(k=k)
        return 0.0

    # 1. k most similar cases by query alone
    sims = [(case, query_similarity(query, case.query)) for case in case_base]
    sims.sort(key=lambda x: -x[1])
    top_k = sims[:k]

    # 2. For each, weight by query-similarity * route-overlap
    weights: List[float] = []
    ratings: List[float] = []
    trace_cases: List[CBRTopKCase] = []
    for case, q_sim in top_k:
        r_sim = route_overlap(route, case.chosen_route)
        w = q_sim * r_sim
        trace_cases.append(
            CBRTopKCase(
                case_id=case.case_id,
                query_similarity=round(q_sim, 3),
                route_overlap=round(r_sim, 3),
                rating=case.rating,
                weight=round(w, 3),
            )
        )
        if r_sim <= 0:
            continue
        if w <= 0:
            continue
        weights.append(w)
        ratings.append(case.rating)

    if not weights:
        if return_trace:
            return 0.0, CBRTrace(k=k, top_cases=trace_cases)
        return 0.0

    total_w = sum(weights)
    weighted_avg = sum(r * w for r, w in zip(ratings, weights)) / total_w
    normalized = max(0.0, min(1.0, (weighted_avg - 1.0) / 4.0))

    if return_trace:
        trace = CBRTrace(
            k=k,
            top_cases=trace_cases,
            weighted_avg_rating=round(weighted_avg, 3),
            normalized_score=round(normalized, 3),
        )
        return normalized, trace
    return normalized


__all__ = ["query_similarity", "route_overlap", "score_route"]
