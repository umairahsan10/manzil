"""
Route enumeration — Phase 2.

Builds ordered destination chains from the filtered feasible set, pruning
chains that would have an impractical single-leg drive or would visit too
many destinations for the available days.

Constraints (defaults; tunable):
    - max_destinations         = 4   (per tech-sketch §4 cap)
    - max_single_leg_hours     = 14  (no humane driving above this)
    - max_routes               = 80  (the diversity selector picks 3 from these)
    - no destination is visited twice in the same chain

The output is a list of `EnumeratedRoute` objects, each carrying the
ordered destination ids plus the aggregated inter-destination drive hours.
The origin → first-stop leg is computed downstream when we know the origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from manzil.data_loader import load_road_knowledge


@dataclass
class EnumeratedRoute:
    destinations: List[str]
    inter_drive_hours: float  # sum of drive-time across stop-to-stop legs (excludes origin)
    has_complete_road_data: bool

    @property
    def n_stops(self) -> int:
        return len(self.destinations)


def _segment_lookup(road_knowledge: Dict, a: str, b: str) -> Optional[Dict]:
    """Try both `a__b` and `b__a` (route is symmetric in our data model)."""
    segments = road_knowledge.get("segments", {})
    seg = segments.get(f"{a}__{b}") or segments.get(f"{b}__{a}")
    return seg


def enumerate_routes(
    feasible_ids: List[str],
    *,
    max_destinations: int = 4,
    max_single_leg_hours: float = 14.0,
    max_routes: int = 80,
) -> List[EnumeratedRoute]:
    """Generate ordered destination chains from the feasible set."""
    rk = load_road_knowledge()

    all_routes: List[EnumeratedRoute] = []

    # Single-destination chains: every feasible destination on its own
    for d in feasible_ids:
        all_routes.append(
            EnumeratedRoute(
                destinations=[d],
                inter_drive_hours=0.0,
                has_complete_road_data=True,
            )
        )

    # BFS extension to longer chains
    frontier: List[EnumeratedRoute] = [r for r in all_routes if r.n_stops == 1]
    while frontier and len(all_routes) < max_routes * 4:
        chain = frontier.pop(0)
        if chain.n_stops >= max_destinations:
            continue
        last = chain.destinations[-1]
        for nxt in feasible_ids:
            if nxt in chain.destinations:
                continue  # no revisits
            seg = _segment_lookup(rk, last, nxt)
            if seg is None:
                continue
            leg_hours = float(seg.get("drive_time_hours", 0.0))
            if leg_hours > max_single_leg_hours:
                continue
            extended = EnumeratedRoute(
                destinations=chain.destinations + [nxt],
                inter_drive_hours=chain.inter_drive_hours + leg_hours,
                has_complete_road_data=chain.has_complete_road_data,
            )
            all_routes.append(extended)
            frontier.append(extended)

    # Prefer longer chains (more interesting trips) but with reasonable drive
    # times. We keep `max_routes` total, biased toward multi-stop.
    all_routes.sort(
        key=lambda r: (-r.n_stops, r.inter_drive_hours)
    )
    return all_routes[:max_routes]


__all__ = ["EnumeratedRoute", "enumerate_routes"]
