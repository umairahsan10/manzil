"""Feedback endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from manzil.memory.feedback import get_feedback_stats, submit_feedback, VALID_TAGS
from manzil.schemas import UserQuery
from backend.schemas import FeedbackRequest, FeedbackResponse, FeedbackStatsResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback_endpoint(request: FeedbackRequest):
    """Submit post-trip feedback and append it to the case base."""
    # In Phase 1 the trip isn't persisted on the backend; the frontend sends
    # the trip_id only. For now we create a minimal placeholder query and
    # winner route so the feedback can still train the CBR.
    # Phase 2 will look up the actual trip from Postgres.
    query = UserQuery(
        group_size=1,
        group_composition="solo",
        budget_pkr=100000,
        days=5,
        travel_month=6,
        travel_mode_pref="road",
        origin_city="islamabad",
        difficulty_tolerance=3,
    )

    tags = [t for t in request.tags if t in VALID_TAGS]

    try:
        entry = submit_feedback(
            query=query,
            winner_route=["placeholder"],
            travel_modes=["road"],
            rating=request.rating,
            tags=tags,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feedback failed: {exc}") from exc

    return {"feedback_id": entry.case_id, "message": "Feedback recorded"}


@router.get("/stats", response_model=FeedbackStatsResponse)
def feedback_stats():
    """Return aggregate feedback statistics."""
    stats = get_feedback_stats()
    # get_feedback_stats returns top_tags as list of (tag, count) tuples;
    # expose just the tag names for the UI.
    top_tags = stats.get("top_tags", [])
    if top_tags and isinstance(top_tags[0], (list, tuple)):
        top_tags = [tag for tag, _ in top_tags]
    return {
        "count": stats.get("count", 0),
        "avg_rating": stats.get("avg_rating", 0.0),
        "top_tags": top_tags,
    }
