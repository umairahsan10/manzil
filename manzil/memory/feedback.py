"""
Feedback loop — Phase 4.

submit_feedback() builds a CaseBaseEntry from a real user's post-trip
feedback and appends it atomically to data/case_base.json. The CBR step
in the recommender reads this file fresh on every call, so the loop
closes immediately.

Atomic write pattern: write to a temp file in the same directory, then
os.replace() to the target. This prevents partial writes under
simultaneous submissions.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from typing import List

from manzil.data_loader import data_dir, load_case_base
from manzil.schemas import CaseBaseEntry, UserQuery

_CASE_BASE_PATH = data_dir() / "case_base.json"
_WRITE_LOCK = threading.Lock()

# Predefined tag set (used by the UI and validated loosely here)
VALID_TAGS = {
    "too-rushed",
    "too-slow",
    "loved-the-food",
    "weather-was-wrong",
    "budget-overran",
    "budget-under",
    "would-recommend",
    "not-again",
    "great-views",
    "road-was-rough",
    "altitude-sick",
    "family-friendly",
    "stay-mismatch",
}


def submit_feedback(
    query: UserQuery,
    winner_route: List[str],
    travel_modes: List[str],
    rating: float,
    tags: List[str] = None,
    accuracy_scores: dict = None,
) -> CaseBaseEntry:
    """
    Append a real-user feedback entry to the case base atomically.

    Args:
        query: The original UserQuery that produced the recommendation.
        winner_route: Ordered list of destination IDs that were chosen.
        travel_modes: Ordered list of travel mode strings used.
        rating: User rating 1.0–5.0.
        tags: Optional list of feedback tags.
        accuracy_scores: Optional dict with budget_accuracy / safety_accuracy /
            experience_quality (1.0–5.0 each).

    Returns:
        The newly created CaseBaseEntry.
    """
    tags = tags or []
    # Normalize tags to known set
    tags = [t for t in tags if t in VALID_TAGS]
    accuracy_scores = accuracy_scores or {}

    entry = CaseBaseEntry(
        case_id=f"real_{uuid.uuid4().hex[:8]}",
        query=query,
        chosen_route=winner_route,
        travel_modes=travel_modes,
        persona="real_user",
        rating=max(1.0, min(5.0, float(rating))),
        feedback_tags=tags,
        is_synthetic=False,
        accuracy_scores=accuracy_scores,
    )

    _append_case_base(entry)
    return entry


def _append_case_base(entry: CaseBaseEntry) -> None:
    """
    Atomically append a CaseBaseEntry to data/case_base.json.
    Uses a thread lock + temp-file rename for safety.
    """
    path = _CASE_BASE_PATH

    with _WRITE_LOCK:
        # Load existing
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data.append(entry.model_dump(mode="json"))

        # Atomic write via temp file + replace
        dir_name = path.parent
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


def get_feedback_stats() -> dict:
    """
    Return basic stats about the feedback collected so far.
    """
    cases = load_case_base()
    real_cases = [c for c in cases if not c.is_synthetic]
    if not real_cases:
        return {"count": 0, "avg_rating": 0.0, "top_tags": []}

    avg_rating = sum(c.rating for c in real_cases) / len(real_cases)
    tag_counts: dict[str, int] = {}
    for c in real_cases:
        for t in c.feedback_tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "count": len(real_cases),
        "avg_rating": round(avg_rating, 2),
        "top_tags": top_tags,
    }


__all__ = ["submit_feedback", "get_feedback_stats", "VALID_TAGS"]
