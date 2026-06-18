"""API request/response Pydantic models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    cache_enabled: bool
    demo_mode: bool
    full_llm_mode: bool
    cache_dir: str
    llm: Dict[str, Any]
    weather: Dict[str, Any]


class PlanRequest(BaseModel):
    query: Dict[str, Any]
    full_llm_mode: bool = False
    model_config = {"extra": "forbid"}


class PlanResponse(BaseModel):
    trip_id: str
    query: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    recommendation_trace: Optional[Dict[str, Any]] = None
    debate_result: Optional[Dict[str, Any]] = None


class ReplanRequest(BaseModel):
    trip_id: str
    disruption: Dict[str, Any]


class ReplanResponse(BaseModel):
    trip_id: str
    original_result: Dict[str, Any]
    new_result: Dict[str, Any]


class FeedbackRequest(BaseModel):
    trip_id: str
    rating: float = Field(..., ge=1.0, le=5.0)
    tags: List[str] = Field(default_factory=list)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    message: str


class FeedbackStatsResponse(BaseModel):
    count: int
    avg_rating: float
    top_tags: List[str]
