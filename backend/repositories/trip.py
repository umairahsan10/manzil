"""Trip repository interface and Phase 1 JSON implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class TripRepository(ABC):
    """Abstract trip storage. Phase 2 will add a Postgres implementation."""

    @abstractmethod
    def save(self, session_id: str, query: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Save a trip and return its ID."""
        ...

    @abstractmethod
    def get(self, trip_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def list_by_session(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        ...


class JsonTripRepository(TripRepository):
    """In-memory + JSON-file placeholder for Phase 1."""

    def save(self, session_id: str, query: Dict[str, Any], result: Dict[str, Any]) -> str:
        # Phase 1: no-op; Phase 2 will persist to Postgres.
        return "trip-placeholder-id"

    def get(self, trip_id: str) -> Optional[Dict[str, Any]]:
        return None

    def list_by_session(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return []
