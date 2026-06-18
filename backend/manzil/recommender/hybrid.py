"""
Hybrid scorer — Phase 2.

Linear blend of CBR and content-based scores:

    s = alpha * cbr + (1 - alpha) * content

Default `alpha = 0.6`, tuned on a held-out split during evaluation in
Phase 5. Both inputs are in [0, 1]; the output is in [0, 1].
"""

from __future__ import annotations

DEFAULT_ALPHA = 0.6


def hybrid_score(cbr: float, content: float, *, alpha: float = DEFAULT_ALPHA) -> float:
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1]; got {alpha}")
    return alpha * cbr + (1.0 - alpha) * content


__all__ = ["DEFAULT_ALPHA", "hybrid_score"]
