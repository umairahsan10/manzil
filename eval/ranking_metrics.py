"""
Ranking metrics used in the offline recommender evaluation.

Each function takes a list of ranks (1-indexed position of the relevant
item, or None if not found) and returns the metric averaged across queries.
"""

from __future__ import annotations

import math
from typing import List, Optional


def precision_at_k(ranks: List[Optional[int]], k: int = 5) -> float:
    if not ranks:
        return 0.0
    found = sum(1 for r in ranks if r is not None and r <= k)
    return found / len(ranks)


def recall_at_k(ranks: List[Optional[int]], k: int = 5) -> float:
    return precision_at_k(ranks, k=k)


def ndcg_at_k(ranks: List[Optional[int]], k: int = 5) -> float:
    if not ranks:
        return 0.0
    total = 0.0
    for r in ranks:
        if r is None or r > k:
            dcg = 0.0
        else:
            dcg = 1.0 / math.log2(r + 1)
        total += dcg
    return total / len(ranks)


def mrr(ranks: List[Optional[int]]) -> float:
    if not ranks:
        return 0.0
    total = 0.0
    for r in ranks:
        if r is None:
            total += 0.0
        else:
            total += 1.0 / r
    return total / len(ranks)


def format_table(
    rows: List[tuple],
    headers: List[str] = None,
) -> str:
    if headers is None:
        headers = ["Configuration", "P@5", "R@5", "NDCG@5", "MRR"]
    col_widths = [max(len(str(r[i])) for r in rows + [tuple(headers)]) for i in range(len(headers))]
    sep = " | ".join("-" * w for w in col_widths)
    header = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    body = "\n".join(
        " | ".join(str(r[i]).ljust(col_widths[i]) for i in range(len(r)))
        for r in rows
    )
    return f"{header}\n{sep}\n{body}"


__all__ = ["precision_at_k", "recall_at_k", "ndcg_at_k", "mrr", "format_table"]
