"""
Persona-grounded synthetic case-base generator.

Loads `data/personas.json` and `data/destinations.json`, samples ~25 cases per
persona (configurable), and writes `data/case_base.json` as a list of
`CaseBaseEntry` objects.

Each case is a complete `UserQuery` plus a `chosen_route`, `travel_modes`,
`persona`, `rating`, and `feedback_tags`. Ratings are a noisy function of
(persona-preference match, destination match), clamped to 1.0–5.0.

Run from project root:
    python scripts/generate_case_base.py
    python scripts/generate_case_base.py --cases-per-persona 30 --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manzil.data_loader import load_destinations  # noqa: E402
from manzil.schemas import (  # noqa: E402
    CaseBaseEntry,
    GroupType,
    TravelMode,
    UserQuery,
)


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------


def _sample_categorical(rng: random.Random, dist: Dict[str, float]) -> str:
    """Pick a key proportional to its weight."""
    items = list(dist.items())
    keys = [k for k, _ in items]
    weights = [w for _, w in items]
    return rng.choices(keys, weights=weights, k=1)[0]


def _sample_int_range(rng: random.Random, rng_pair: List[int]) -> int:
    lo, hi = rng_pair
    return rng.randint(lo, hi)


def _sample_styles(
    rng: random.Random, weights: Dict[str, float], n_min: int = 1, n_max: int = 3
) -> List[str]:
    """Pick 1-3 styles weighted by the persona's style_weights."""
    n = rng.randint(n_min, n_max)
    items = list(weights.items())
    keys = [k for k, _ in items]
    w = [v for _, v in items]
    if n >= len(keys):
        return list(keys)
    # Sample without replacement, weighted
    chosen: List[str] = []
    pool_keys = keys[:]
    pool_w = w[:]
    for _ in range(n):
        idx = rng.choices(range(len(pool_keys)), weights=pool_w, k=1)[0]
        chosen.append(pool_keys.pop(idx))
        pool_w.pop(idx)
    return chosen


def _sample_difficulty(
    rng: random.Random, mean: float, std: float
) -> int:
    val = rng.gauss(mean, std)
    return max(1, min(5, int(round(val))))


# ---------------------------------------------------------------------------
# Route + rating sampling
# ---------------------------------------------------------------------------


def _sample_route(
    rng: random.Random,
    persona: Dict[str, Any],
    travel_month: int,
    days: int,
    destinations_by_id: Dict[str, Any],
) -> List[str]:
    """
    Pick 1–3 destinations from the persona's preferred pool, filtered by
    season-open in `travel_month`. Falls back to any open destination if
    no preferred ones are open.
    """
    preferred = persona["preferred_destinations"]
    avoided = set(persona.get("avoided_destinations", []))

    open_preferred = [
        d for d in preferred
        if d in destinations_by_id
        and destinations_by_id[d].season_open[travel_month - 1]
    ]
    if not open_preferred:
        open_preferred = [
            d
            for d, dest in destinations_by_id.items()
            if dest.season_open[travel_month - 1] and d not in avoided
        ]
    if not open_preferred:
        return []

    n_dests = 1 if days <= 4 else (2 if days <= 8 else rng.randint(2, 3))
    n_dests = min(n_dests, len(open_preferred))
    chosen = rng.sample(open_preferred, k=n_dests)
    return chosen


def _rate_case(
    rng: random.Random,
    persona: Dict[str, Any],
    chosen_route: List[str],
) -> float:
    preferred = set(persona["preferred_destinations"])
    avoided = set(persona.get("avoided_destinations", []))

    base = 3.5
    for d in chosen_route:
        if d in preferred:
            base += 0.4
        if d in avoided:
            base -= 0.6
    base += rng.gauss(0, 0.3)
    return max(1.0, min(5.0, round(base, 1)))


def _feedback_tags_for(
    rng: random.Random,
    persona: Dict[str, Any],
    rating: float,
    chosen_route: List[str],
    days: int,
) -> List[str]:
    tags: List[str] = []
    if rating >= 4.5:
        tags.append("would-recommend")
    if rating >= 4.0 and "photography" in persona["style_weights"]:
        tags.append("loved-the-views")
    if rating <= 2.5:
        tags.append(rng.choice(["disappointed", "not-as-described"]))
    if days <= 5 and len(chosen_route) >= 2:
        tags.append("too-rushed")
    if days >= 9 and len(chosen_route) == 1:
        tags.append("could-have-added-more")
    if "family" in persona["style_weights"] and rating >= 4.0:
        tags.append("kid-friendly")
    if "adventure" in persona["style_weights"] and rating >= 4.0:
        tags.append("epic-trek")
    return tags


# ---------------------------------------------------------------------------
# Per-persona generation
# ---------------------------------------------------------------------------


def _generate_for_persona(
    rng: random.Random,
    persona: Dict[str, Any],
    n_cases: int,
    destinations_by_id: Dict[str, Any],
) -> List[CaseBaseEntry]:
    out: List[CaseBaseEntry] = []
    attempts = 0
    while len(out) < n_cases and attempts < n_cases * 4:
        attempts += 1
        group_size = _sample_int_range(rng, persona["group_size_range"])
        group_composition = rng.choice(persona["group_compositions"])
        budget = _sample_int_range(rng, persona["budget_band_pkr"])
        days = _sample_int_range(rng, persona["days_band"])
        travel_month = int(_sample_categorical(rng, persona["travel_month_distribution"]))
        travel_mode = _sample_categorical(rng, persona["travel_mode_distribution"])
        origin = _sample_categorical(rng, persona["origin_distribution"])
        styles = _sample_styles(rng, persona["style_weights"])
        difficulty = _sample_difficulty(
            rng,
            persona["difficulty_tolerance_mean"],
            persona["difficulty_tolerance_std"],
        )

        chosen_route = _sample_route(
            rng, persona, travel_month, days, destinations_by_id
        )
        if not chosen_route:
            continue  # no feasible destinations this month for this persona

        # travel_modes vector: one entry per segment (origin->stop1, stop1->stop2, ...)
        n_segments = len(chosen_route)
        travel_modes = [TravelMode(travel_mode)] * n_segments

        rating = _rate_case(rng, persona, chosen_route)
        tags = _feedback_tags_for(rng, persona, rating, chosen_route, days)

        query = UserQuery(
            group_size=group_size,
            group_composition=GroupType(group_composition),
            budget_pkr=budget,
            days=days,
            travel_month=travel_month,
            travel_mode_pref=TravelMode(travel_mode),
            origin_city=origin,
            style_tags=styles,
            difficulty_tolerance=difficulty,
            preferred_destinations=[],
            hard_constraints=[],
        )
        out.append(
            CaseBaseEntry(
                case_id=f"{persona['id']}-{uuid.UUID(int=rng.getrandbits(128)).hex[:8]}",
                query=query,
                chosen_route=chosen_route,
                travel_modes=travel_modes,
                persona=persona["id"],
                rating=rating,
                feedback_tags=tags,
                is_synthetic=True,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cases-per-persona", type=int, default=25)
    parser.add_argument(
        "--out",
        type=str,
        default=str(_ROOT / "data" / "case_base.json"),
        help="Output path; defaults to data/case_base.json",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    with (_ROOT / "data" / "personas.json").open("r", encoding="utf-8") as f:
        persona_doc = json.load(f)
    personas = persona_doc["personas"]

    destinations_by_id = load_destinations()

    all_cases: List[CaseBaseEntry] = []
    for persona in personas:
        cases = _generate_for_persona(
            rng, persona, args.cases_per_persona, destinations_by_id
        )
        print(f"  {persona['id']:<24} {len(cases):>3} cases")
        all_cases.extend(cases)

    # Stable order: by persona, then by case_id
    all_cases.sort(key=lambda e: (e.persona, e.case_id))

    payload = [e.model_dump(mode="json") for e in all_cases]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(all_cases)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
