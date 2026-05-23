"""
Content-based scoring — Phase 2.

Cosine similarity between the user's style preferences and the route's
aggregate activity profile, blended with a difficulty-match score.

Output is in [0.0, 1.0]:
    content_score = 0.7 * tag_cosine + 0.3 * difficulty_match

The user vector is soft: picked tags score 1.0, unpicked tags score their
highest semantic similarity to any picked tag (e.g. "trekking" gets 0.8
credit when user picks "adventure"). This prevents penalising routes that
contain closely related but non-identical tags.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from manzil.schemas import ContentTagVector, ContentTrace, Destination, UserQuery

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

# Pairwise semantic similarity between tags. Stored as (smaller, larger) tuples
# so lookup is order-independent. Pairs absent from this dict have similarity 0.
_TAG_SIMILARITY: Dict[Tuple[str, str], float] = {
    # Outdoor / active cluster
    ("adventure", "trekking"):    0.8,
    ("adventure", "mountain"):    0.6,
    ("adventure", "wildlife"):    0.4,
    ("adventure", "photography"): 0.3,
    ("adventure", "lake"):        0.2,
    ("adventure", "family"):      0.1,
    ("mountain",  "trekking"):    0.7,
    ("mountain",  "photography"): 0.5,
    ("mountain",  "lake"):        0.4,
    ("mountain",  "wildlife"):    0.3,
    ("mountain",  "family"):      0.2,
    ("trekking",  "wildlife"):    0.3,
    ("trekking",  "photography"): 0.3,
    ("trekking",  "lake"):        0.2,
    # Nature / scenic cluster
    ("photography", "wildlife"):  0.5,
    ("photography", "lake"):      0.4,
    ("photography", "relaxation"):0.2,
    ("lake",       "wildlife"):   0.3,
    ("lake",       "relaxation"): 0.5,
    ("lake",       "family"):     0.3,
    ("wildlife",   "relaxation"): 0.2,
    # Culture / history cluster
    ("cultural",   "history"):    0.7,
    ("cultural",   "shopping"):   0.4,
    ("cultural",   "photography"):0.3,
    ("cultural",   "family"):     0.3,
    ("cultural",   "relaxation"): 0.2,
    ("history",    "photography"):0.3,
    ("history",    "shopping"):   0.2,
    ("history",    "relaxation"): 0.1,
    ("history",    "family"):     0.2,
    # Leisure / social cluster
    ("family",     "relaxation"): 0.5,
    ("family",     "shopping"):   0.3,
    ("family",     "wildlife"):   0.3,
    ("family",     "photography"):0.2,
    ("relaxation", "shopping"):   0.2,
    # Transit is mostly logistical — low cross-similarity
    ("shopping",   "transit"):    0.1,
}


def _tag_sim(a: str, b: str) -> float:
    """Symmetric pairwise tag similarity. Returns 0 for unknown pairs."""
    key: Tuple[str, str] = (min(a, b), max(a, b))
    return _TAG_SIMILARITY.get(key, 0.0)


def _soft_user_vec(style_tags: List[str]) -> List[float]:
    """
    Soft user preference vector.

    Picked tags   → 1.0
    Unpicked tags → highest similarity score to any picked tag (or 0.0)

    Example: user picks ["adventure"]. "trekking" gets 0.8, "mountain" gets
    0.6, "shopping" gets 0.0. This lets the cosine reward routes whose tags
    are semantically close to what the user asked for.
    """
    picked = {t.lower() for t in style_tags}
    vec: List[float] = []
    for t in _TAG_UNIVERSE:
        if t in picked:
            vec.append(1.0)
        else:
            credit = max((_tag_sim(t, p) for p in picked), default=0.0)
            vec.append(credit)
    return vec


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
    *,
    return_trace: bool = False,
) -> float | tuple[float, ContentTrace]:
    """Return a content score in [0.0, 1.0] for the route under this query.
    If return_trace=True, returns (score, ContentTrace)."""
    if not route:
        if return_trace:
            return 0.0, ContentTrace()
        return 0.0

    user_vec = _soft_user_vec(query.style_tags)
    route_vec = _route_tag_vec(route, destinations)
    tag_cos = _cosine(user_vec, route_vec)
    diff_match = _difficulty_match(route, destinations, query.difficulty_tolerance)

    content_score = 0.7 * tag_cos + 0.3 * diff_match

    if return_trace:
        tag_vectors = [
            ContentTagVector(tag=t, user_value=u, route_value=r)
            for t, u, r in zip(_TAG_UNIVERSE, user_vec, route_vec)
        ]
        diffs = [
            destinations[d].difficulty
            for d in route
            if d in destinations
        ]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0.0
        trace = ContentTrace(
            tag_cosine=round(tag_cos, 3),
            difficulty_match=round(diff_match, 3),
            content_score=round(content_score, 3),
            user_vector=tag_vectors,
            avg_route_difficulty=round(avg_diff, 2),
            user_tolerance=query.difficulty_tolerance,
        )
        return content_score, trace

    return content_score


__all__ = ["score_route"]
