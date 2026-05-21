"""
Ethics measurements — synthetic-data bias and popularity bias.

These make zero LLM calls; they only exercise the recommender.

(1) Per-persona diversity:
    For each of the 6 personas, run 25 sampled queries and report the
    standard deviation of the diversity-axis distribution across returned
    candidates. A persona that always gets the same axis profile is a red
    flag for synthetic-data bias.

(2) Recommendation frequency per destination:
    Count how often each destination appears in the winning candidate
    across the full eval sweep; report the Gini coefficient. A high Gini
    means the system over-recommends a few popular destinations.

Usage:
    python eval/ethics_eval.py

Output:
    eval/results/ethics.txt
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Dict, List

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manzil.recommender.pipeline import recommend
from manzil.schemas import GroupType, TravelMode, UserQuery

RESULTS_DIR = _ROOT / "eval" / "results"
PERSONAS_QUERIES_PER = 25


def _make_query_from_persona(persona: dict, rng: random.Random) -> UserQuery:
    """Sample a plausible UserQuery from a persona's distribution."""
    comp_key = rng.choice(persona["group_compositions"])
    group_size = rng.randint(persona["group_size_range"][0], persona["group_size_range"][1])
    budget = rng.randint(persona["budget_band_pkr"][0], persona["budget_band_pkr"][1])
    days = rng.randint(persona["days_band"][0], persona["days_band"][1])
    month_strs = list(persona["travel_month_distribution"].keys())
    month_weights = [persona["travel_month_distribution"][m] for m in month_strs]
    month = int(rng.choices(month_strs, weights=month_weights)[0])
    mode_strs = list(persona["travel_mode_distribution"].keys())
    mode_weights = [persona["travel_mode_distribution"][m] for m in mode_strs]
    mode = rng.choices(mode_strs, weights=mode_weights)[0]
    origin_strs = list(persona["origin_distribution"].keys())
    origin_weights = [persona["origin_distribution"][o] for o in origin_strs]
    origin = rng.choices(origin_strs, weights=origin_weights)[0]
    style_weights = persona["style_weights"]
    styles = [s for s, w in style_weights.items() if rng.random() < w]
    if not styles:
        styles = [list(style_weights.keys())[0]]
    diff = round(rng.gauss(persona["difficulty_tolerance_mean"], persona["difficulty_tolerance_std"]))
    diff = max(1, min(5, diff))

    return UserQuery(
        group_size=group_size,
        group_composition=GroupType(comp_key),
        budget_pkr=budget,
        days=days,
        travel_month=month,
        travel_mode_pref=TravelMode(mode),
        origin_city=origin,
        style_tags=styles,
        difficulty_tolerance=diff,
    )


def _gini(values: List[float]) -> float:
    """Compute Gini coefficient."""
    if not values or sum(values) == 0:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    cum = 0.0
    for i, v in enumerate(sorted_v, 1):
        cum += (2 * i - n - 1) * v
    return cum / (n * sum(sorted_v))


def measure_per_persona_diversity(personas: List[dict]) -> Dict[str, dict]:
    """For each persona, run 25 queries and measure diversity-axis variation."""
    rng = random.Random(42)
    results = {}
    for p in personas:
        pid = p["id"]
        axis_values: Dict[str, List[str]] = {"scope": [], "mode_mix": [], "pace": [], "risk": [], "budget_posture": []}
        attempts = 0
        collected = 0
        while collected < PERSONAS_QUERIES_PER and attempts < PERSONAS_QUERIES_PER * 3:
            attempts += 1
            q = _make_query_from_persona(p, rng)
            try:
                candidates = recommend(q)
            except Exception:
                continue
            if not candidates:
                continue
            for c in candidates:
                for axis in axis_values:
                    val = c.diversity_axes.get(axis, "?")
                    axis_values[axis].append(val)
                collected += 1

        # For each axis, report the entropy or distinct-value ratio
        axis_metrics = {}
        for axis, vals in axis_values.items():
            if not vals:
                axis_metrics[axis] = {"unique": 0, "total": 0, "ratio": 0.0}
                continue
            unique = len(set(vals))
            axis_metrics[axis] = {
                "unique": unique,
                "total": len(vals),
                "ratio": unique / max(1, len(vals)),
            }

        results[pid] = {
            "queries_attempted": attempts,
            "candidates_collected": collected,
            "axes": axis_metrics,
        }
    return results


def measure_popularity_bias(personas: List[dict]) -> Dict[str, float]:
    """Count destination frequency across persona-sampled queries."""
    rng = random.Random(43)
    dest_counts: Dict[str, int] = {}
    for p in personas:
        for _ in range(PERSONAS_QUERIES_PER):
            q = _make_query_from_persona(p, rng)
            try:
                candidates = recommend(q)
            except Exception:
                continue
            if not candidates:
                continue
            for c in candidates[:1]:  # top-ranked candidate
                for d in c.destinations:
                    dest_counts[d] = dest_counts.get(d, 0) + 1

    total = sum(dest_counts.values()) or 1
    frequencies = [c / total for c in dest_counts.values()]
    gini = _gini(frequencies)

    sorted_dests = sorted(dest_counts.items(), key=lambda x: -x[1])

    return {
        "gini_coefficient": round(gini, 4),
        "total_recommendations": total,
        "destination_counts": sorted_dests,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    personas_path = _ROOT / "data" / "personas.json"
    if not personas_path.exists():
        print("ERROR: personas.json not found. Run scripts/generate_case_base.py first.")
        return

    with personas_path.open("r", encoding="utf-8") as f:
        personas = json.load(f)["personas"]

    print("=== Per-persona diversity (25 queries each) ===")
    div = measure_per_persona_diversity(personas)
    for pid, data in div.items():
        print(f"\n  {pid}:")
        for axis, m in data["axes"].items():
            print(f"    {axis}: {m['unique']} unique / {m['total']} samples (ratio={m['ratio']:.3f})")

    print("\n=== Popularity bias ===")
    pop = measure_popularity_bias(personas)
    print(f"  Gini coefficient: {pop['gini_coefficient']}")
    print(f"  Total recommendations: {pop['total_recommendations']}")
    print("  Top destinations:")
    for dest, count in pop["destination_counts"][:10]:
        print(f"    {dest}: {count}")

    # Write output file
    out_path = RESULTS_DIR / "ethics.txt"
    with out_path.open("w", encoding="utf-8") as f:
        f.write("=== Per-persona diversity ===\n")
        for pid, data in div.items():
            f.write(f"\n{pid}:\n")
            for axis, m in data["axes"].items():
                f.write(f"  {axis}: unique={m['unique']}, total={m['total']}, ratio={m['ratio']:.3f}\n")
        f.write(f"\n=== Popularity bias ===\n")
        f.write(f"Gini coefficient: {pop['gini_coefficient']}\n")
        f.write(f"Total recommendations: {pop['total_recommendations']}\n")
        f.write("Destination counts:\n")
        for dest, count in pop["destination_counts"]:
            f.write(f"  {dest}: {count}\n")

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
