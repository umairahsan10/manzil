"""
Hard-constraint filter — Phase 2.

Drops any destination whose attributes violate the user's hard constraints
*before* the recommender wastes cycles enumerating routes through it.
Returns the surviving set plus a human-readable record of what was dropped
and why — the relaxation layer reads that record to decide what to loosen.

Hard constraints checked here:
    - season_open[travel_month-1] is False         → SEASON_CLOSED
    - difficulty > query.difficulty_tolerance      → TOO_DIFFICULT
    - group_composition not in group_suitability   → GROUP_MISMATCH
    - hard_constraints includes 'wheelchair'       → ACCESSIBLE_REQUIRED
                                                     and !destination.accessible
    - hard_constraints includes 'foreign-passport' → NOC_REQUIRED
                                                     and destination.noc_required
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from manzil.schemas import Destination, UserQuery


# ---------------------------------------------------------------------------
# Filter result
# ---------------------------------------------------------------------------


@dataclass
class FilterReason:
    destination_id: str
    code: str       # SEASON_CLOSED | TOO_DIFFICULT | GROUP_MISMATCH | ACCESSIBLE_REQUIRED | NOC_REQUIRED
    detail: str


@dataclass
class FilterResult:
    feasible: Dict[str, Destination]
    dropped: List[FilterReason] = field(default_factory=list)

    @property
    def feasible_ids(self) -> List[str]:
        return list(self.feasible.keys())

    def dropped_for(self, code: str) -> List[FilterReason]:
        return [r for r in self.dropped if r.code == code]


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


def filter_destinations(
    query: UserQuery,
    destinations: Dict[str, Destination],
) -> FilterResult:
    feasible: Dict[str, Destination] = {}
    dropped: List[FilterReason] = []

    wheelchair_required = any(
        c.lower() in {"wheelchair", "wheelchair-accessible", "accessible"}
        for c in query.hard_constraints
    )
    foreigner = any(
        c.lower() in {"foreign-passport", "foreigner", "noc-sensitive"}
        for c in query.hard_constraints
    )

    for dest_id, dest in destinations.items():
        # 1. Season
        if not dest.season_open[query.travel_month - 1]:
            dropped.append(
                FilterReason(
                    dest_id,
                    "SEASON_CLOSED",
                    f"closed in month {query.travel_month}",
                )
            )
            continue

        # 2. Difficulty
        if dest.difficulty > query.difficulty_tolerance:
            dropped.append(
                FilterReason(
                    dest_id,
                    "TOO_DIFFICULT",
                    f"difficulty {dest.difficulty} > tolerance {query.difficulty_tolerance}",
                )
            )
            continue

        # 3. Group suitability
        if dest.group_suitability and (
            query.group_composition.value not in dest.group_suitability
        ):
            dropped.append(
                FilterReason(
                    dest_id,
                    "GROUP_MISMATCH",
                    f"group '{query.group_composition.value}' not in {dest.group_suitability}",
                )
            )
            continue

        # 4. Wheelchair accessibility
        if wheelchair_required and not dest.accessible:
            dropped.append(
                FilterReason(
                    dest_id,
                    "ACCESSIBLE_REQUIRED",
                    "destination is not wheelchair-accessible",
                )
            )
            continue

        # 5. Foreigner / NOC
        if foreigner and dest.noc_required_for_foreigners:
            dropped.append(
                FilterReason(
                    dest_id,
                    "NOC_REQUIRED",
                    "destination requires foreign-traveller NOC",
                )
            )
            continue

        feasible[dest_id] = dest

    return FilterResult(feasible=feasible, dropped=dropped)


__all__ = ["FilterResult", "FilterReason", "filter_destinations"]
