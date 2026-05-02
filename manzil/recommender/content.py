"""
Content-based scoring — Phase 2.

Cosine similarity between the user's style preferences and the route's
aggregate activity profile, blended with a difficulty-match score.

Output is in [0.0, 1.0]:
    content_score = 0.7 * tag_cosine + 0.3 * difficulty_match
"""

from __future__ import annotations

import math
from typing import Dict, List

from manzil.schemas import Destination, UserQuery

# Universe of activity tags that the cosine vectors live in. Must contain
# every value that appears in destinations' `activity_tags` AND every value
# the UI lets the user pick as a style. Order is irrelevant — we sort.
_TAG_UNIVERSE = sorted(
    {
        "adventure",
        "cultural",
        "family",
        "history",
        "lake",
        "mountain",
        "photography",
        "relaxation",
        "shopping",
        "transit",
        "trekking",
        "wildlife",
    }
)


def _vec(tags: List[str]) -> List[float]:
    bag = {t.lower() for t in tags}
    return [1.0 if t in bag else 0.0 for t in _TAG_UNIVERSE]


def _route_tag_vec(route: List[str], destinations: Dict[str, Destination]) -> List[float]:
    """Sum of per-destination tag vectors. Captures emphasis when the same tag
    appears across multiple stops."""
    total = [0.0] * len(_TAG_UNIVERSE)
    for dest_id in route:
        dest = destinations.get(dest_id)
        if dest is None:
            continue
        for i, t in enumerate(_TAG_UNIVERSE):
            if t in {x.lower() for x in dest.activity_tags}:
                total[i] += 1.0
    return total


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _difficulty_match(route: List[str], destinations: Dict[str, Destination], tolerance: int) -> float:
    if not route:
        return 0.0
    diffs = [
        destinations[d].difficulty
        for d in route
        if d in destinations
    ]
    if not diffs:
        return 0.0
    avg = sum(diffs) / len(diffs)
    # 1.0 when avg matches tolerance exactly; degrades linearly with distance.
    return max(0.0, 1.0 - abs(avg - tolerance) / 5.0)


def score_route(
    route: List[str],
    query: UserQuery,
    destinations: Dict[str, Destination],
) -> float:
    """Return a content score in [0.0, 1.0] for the route under this query."""
    if not route:
        return 0.0

    user_vec = _vec(query.style_tags)
    route_vec = _route_tag_vec(route, destinations)
    tag_cos = _cosine(user_vec, route_vec)
    diff_match = _difficulty_match(route, destinations, query.difficulty_tolerance)

    return 0.7 * tag_cos + 0.3 * diff_match


__all__ = ["score_route"]
