"""
Constraint relaxation — Phase 2.

When the strict pipeline (filter → enumerate → score) yields zero feasible
routes, the recommender does NOT fail silently. It instead asks this
module to loosen the soft constraints in priority order, retrying after
each step until one produces results.

Priority order (cumulative — each step keeps the previous loosenings):
    1. Increase budget by 15%
    2. ... and reduce days by 1
    3. ... and bump difficulty_tolerance by 1 (if not already at 5)

Each step yields a modified `UserQuery` plus a human-readable note that
the UI surfaces as a banner above the candidate cards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List

from manzil.schemas import UserQuery

BUDGET_BUMP = 0.15  # 15%


@dataclass
class RelaxationStep:
    query: UserQuery
    note: str


def relax(original: UserQuery) -> Iterator[RelaxationStep]:
    """Yields successive cumulative relaxations of `original`."""
    # Step 1 — bump budget
    bumped_budget = int(original.budget_pkr * (1 + BUDGET_BUMP))
    notes_1 = [
        f"increased budget by {int(BUDGET_BUMP * 100)}% (PKR {bumped_budget:,})"
    ]
    yield RelaxationStep(
        query=original.model_copy(update={"budget_pkr": bumped_budget}),
        note=_compose_note(notes_1),
    )

    # Step 2 — also drop a day (only if days >= 3, our schema's lower bound is 2)
    if original.days >= 3:
        notes_2 = notes_1 + [f"reduced days from {original.days} to {original.days - 1}"]
        yield RelaxationStep(
            query=original.model_copy(
                update={
                    "budget_pkr": bumped_budget,
                    "days": original.days - 1,
                }
            ),
            note=_compose_note(notes_2),
        )

    # Step 3 — also raise difficulty tolerance (only if < 5)
    if original.difficulty_tolerance < 5:
        notes_3 = notes_1 + [
            f"raised difficulty tolerance from {original.difficulty_tolerance} "
            f"to {original.difficulty_tolerance + 1}"
        ]
        if original.days >= 3:
            notes_3 = notes_3 + [
                f"reduced days from {original.days} to {original.days - 1}"
            ]
        yield RelaxationStep(
            query=original.model_copy(
                update={
                    "budget_pkr": bumped_budget,
                    "days": max(2, original.days - 1) if original.days >= 3 else original.days,
                    "difficulty_tolerance": original.difficulty_tolerance + 1,
                }
            ),
            note=_compose_note(notes_3),
        )


def _compose_note(notes: List[str]) -> str:
    if not notes:
        return ""
    if len(notes) == 1:
        prefix = "No routes matched your exact constraints. Showing options if you "
        return prefix + notes[0] + "."
    return (
        "No routes matched your exact constraints. Showing options if you "
        + ", ".join(notes[:-1])
        + " and "
        + notes[-1]
        + "."
    )


__all__ = ["RelaxationStep", "relax"]
