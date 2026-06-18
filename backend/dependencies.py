"""FastAPI dependencies (DB session, repositories, etc.)."""

from __future__ import annotations

from backend.repositories.feedback import FeedbackRepository, JsonFeedbackRepository
from backend.repositories.trip import TripRepository, JsonTripRepository


def get_trip_repository() -> TripRepository:
    """Return the active trip repository."""
    return JsonTripRepository()


def get_feedback_repository() -> FeedbackRepository:
    """Return the active feedback repository."""
    return JsonFeedbackRepository()
