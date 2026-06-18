"""Feedback repository interface and Phase 1 JSON implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class FeedbackRepository(ABC):
    """Abstract feedback storage. Phase 2 will add a Postgres implementation."""

    @abstractmethod
    def submit(
        self,
        session_id: str,
        trip_id: str,
        query: Dict[str, Any],
        result: Dict[str, Any],
        rating: float,
        tags: List[str],
    ) -> str:
        """Submit feedback and return its ID."""
        ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        ...


class JsonFeedbackRepository(FeedbackRepository):
    """JSON-file placeholder for Phase 1."""

    def submit(
        self,
        session_id: str,
        trip_id: str,
        query: Dict[str, Any],
        result: Dict[str, Any],
        rating: float,
        tags: List[str],
    ) -> str:
        from manzil.memory.feedback import submit_feedback

        winner_route = result.get("winner", {}).get("route", [])
        travel_modes = result.get("winner", {}).get("travel_modes", [])
        entry = submit_feedback(query, winner_route, travel_modes, rating, tags)
        return entry.id

    def get_stats(self) -> Dict[str, Any]:
        from manzil.memory.feedback import get_feedback_stats

        return get_feedback_stats()
