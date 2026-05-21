"""
Offline recommender evaluation — 80/20 split, 4 configurations.

Usage:
    python eval/run_recommender_eval.py

Output (printed to stdout and saved to eval/results/ranking.txt):
    Configuration | P@5  | R@5  | NDCG@5 |  MRR
    ------------- | ---- | ---- | ------ | -----
    (a) filter-only    | 0.12 | 0.12 |  0.08 | 0.06
    (b) filter+content | 0.31 | 0.31 |  0.22 | 0.18
    (c) filter+CBR     | 0.38 | 0.38 |  0.27 | 0.21
    (d) full hybrid    | 0.44 | 0.44 |  0.33 | 0.27
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manzil.data_loader import load_case_base, load_destinations
from manzil.recommender import cbr, content, diversity
from manzil.recommender.enumerate import EnumeratedRoute, enumerate_routes
from manzil.recommender.filter import filter_destinations
from manzil.schemas import (
    CaseBaseEntry,
    Destination,
    RouteCandidate,
    UserQuery,
)
from manzil.tools.cost_calc import estimate_cost as _full_estimate_cost

from eval.ranking_metrics import (
    format_table,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

SPLIT = float(__import__("os").environ.get("EVAL_SPLIT", "0.8"))
SEED = int(__import__("os").environ.get("EVAL_SEED", "42"))
RESULTS_DIR = _ROOT / "eval" / "results"


def _train_test_split(
    cases: List[CaseBaseEntry],
    split: float = SPLIT,
    seed: int = SEED,
) -> Tuple[List[CaseBaseEntry], List[CaseBaseEntry]]:
    rng = random.Random(seed)
    shuffled = list(cases)
    rng.shuffle(shuffled)
    n_train = max(1, int(len(shuffled) * split))
    return shuffled[:n_train], shuffled[n_train:]


def _chosen_route_rank(
    candidates: List[RouteCandidate],
    chosen_route: List[str],
) -> Optional[int]:
    chosen_set = set(chosen_route)
    for i, c in enumerate(candidates):
        if set(c.destinations) == chosen_set:
            return i + 1
    return None


# ---------------------------------------------------------------------------
# Per-config scoring helpers
# ---------------------------------------------------------------------------


def _build_candidate(
    route: EnumeratedRoute,
    query: UserQuery,
    destinations: Dict[str, Destination],
    idx: int,
    *,
    cbr_score: float = 0.0,
    content_score: float = 0.0,
    axes: Optional[Dict[str, str]] = None,
) -> RouteCandidate:
    cost = _full_estimate_cost(
        RouteCandidate(
            candidate_id=f"eval-{idx}",
            label="",
            destinations=route.destinations,
            travel_modes=[query.travel_mode_pref] * max(1, len(route.destinations)),
            estimated_cost=0,
            days=query.days,
        ),
        query,
    ).total

    if axes is None:
        axes = diversity.compute_axes(route.destinations, query, destinations, cost)

    return RouteCandidate(
        candidate_id=f"eval-{idx}",
        label="",
        destinations=route.destinations,
        travel_modes=[query.travel_mode_pref] * max(1, len(route.destinations)),
        estimated_cost=cost,
        days=query.days,
        diversity_axes=axes,
        cbr_score=cbr_score,
        content_score=content_score,
        rationale="",
    )


def _config_filter_only(
    query: UserQuery,
    destinations: Dict[str, Destination],
) -> List[RouteCandidate]:
    fr = filter_destinations(query, destinations)
    if not fr.feasible:
        return []
    routes = enumerate_routes(list(fr.feasible.keys()))
    return [
        _build_candidate(r, query, destinations, i)
        for i, r in enumerate(routes)
    ]


def _config_content(
    query: UserQuery,
    destinations: Dict[str, Destination],
) -> List[RouteCandidate]:
    fr = filter_destinations(query, destinations)
    if not fr.feasible:
        return []
    routes = enumerate_routes(list(fr.feasible.keys()))
    scored = []
    for i, r in enumerate(routes):
        cs = content.score_route(r.destinations, query, destinations)
        scored.append((cs, _build_candidate(r, query, destinations, i, content_score=cs)))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]


def _config_cbr(
    query: UserQuery,
    destinations: Dict[str, Destination],
    train_cases: List[CaseBaseEntry],
) -> List[RouteCandidate]:
    fr = filter_destinations(query, destinations)
    if not fr.feasible:
        return []
    routes = enumerate_routes(list(fr.feasible.keys()))
    scored = []
    for i, r in enumerate(routes):
        cs = cbr.score_route(r.destinations, query, train_cases)
        scored.append((cs, _build_candidate(r, query, destinations, i, cbr_score=cs)))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]


def _config_full_hybrid(
    query: UserQuery,
    destinations: Dict[str, Destination],
    train_cases: List[CaseBaseEntry],
) -> List[RouteCandidate]:
    fr = filter_destinations(query, destinations)
    if not fr.feasible:
        return []
    routes = enumerate_routes(list(fr.feasible.keys()))
    scored = []
    for i, r in enumerate(routes):
        cbr_s = cbr.score_route(r.destinations, query, train_cases)
        content_s = content.score_route(r.destinations, query, destinations)
        axes = diversity.compute_axes(
            r.destinations, query, destinations,
            _full_estimate_cost(
                RouteCandidate(
                    candidate_id=f"eval-{i}", label="",
                    destinations=r.destinations,
                    travel_modes=[query.travel_mode_pref] * max(1, len(r.destinations)),
                    estimated_cost=0, days=query.days,
                ), query,
            ).total,
        )
        scored.append(
            _build_candidate(r, query, destinations, i, cbr_score=cbr_s, content_score=content_s, axes=axes)
        )
    picked = diversity.pick_diverse_three(scored)
    for letter, c in zip("ABC", picked):
        c.candidate_id = f"cand-{letter}"
    return picked


# ---------------------------------------------------------------------------
# Config registry
# ---------------------------------------------------------------------------

CONFIGS = [
    ("(a) filter-only", _config_filter_only, False),
    ("(b) filter+content", _config_content, False),
    ("(c) filter+CBR", _config_cbr, True),
    ("(d) full hybrid", _config_full_hybrid, True),
]


def evaluate() -> List[Tuple[str, float, float, float, float]]:
    destinations = load_destinations()
    all_cases = load_case_base()

    if not all_cases:
        print("ERROR: case base is empty. Run scripts/generate_case_base.py first.")
        return []

    train, test = _train_test_split(all_cases)
    print(f"Train: {len(train)} cases, Test: {len(test)} cases")

    rows = []
    for name, config_fn, needs_cases in CONFIGS:
        ranks: List[Optional[int]] = []
        for tc in test:
            query = tc.query
            if needs_cases:
                candidates = config_fn(query, destinations, train)
            else:
                candidates = config_fn(query, destinations)
            if not candidates:
                ranks.append(None)
                continue
            rank = _chosen_route_rank(candidates, tc.chosen_route)
            ranks.append(rank)

        p5 = precision_at_k(ranks, k=5)
        r5 = recall_at_k(ranks, k=5)
        n5 = ndcg_at_k(ranks, k=5)
        mr = mrr(ranks)
        rows.append((name, f"{p5:.3f}", f"{r5:.3f}", f"{n5:.3f}", f"{mr:.3f}"))

    return rows


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = evaluate()
    if not rows:
        print("No results produced.")
        return

    table = format_table(rows)
    print("\n" + table + "\n")

    out_path = RESULTS_DIR / "ranking.txt"
    out_path.write_text(table, encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
