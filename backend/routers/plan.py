"""Trip planning endpoints."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from manzil.agents.base import is_full_llm_mode, set_full_llm_mode
from manzil.graph.debate_graph import run_debate, run_debate_stream
from manzil.recommender.pipeline import recommend_with_trace
from manzil.schemas import UserQuery
from manzil.data_loader import load_destinations
from backend.schemas import PlanRequest, PlanResponse

router = APIRouter(prefix="/plan", tags=["plan"])


def _serialize(obj: Any) -> Any:
    """Serialize Pydantic models or other objects to JSON-compatible dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _heuristic_scores(candidate: Any, query: UserQuery) -> dict:
    """Cheap client-useful scores derived from destination metadata — no LLM."""
    destinations = load_destinations()
    dests = [destinations.get(d) for d in candidate.destinations if d in destinations]
    if not dests:
        return {"safety": 0.5, "weather": 0.5, "budget_fit": 0.5, "trip_score": 0.5}

    # Safety: altitude vs tolerance
    max_alt = max(d.altitude_m for d in dests)
    threshold = 4500
    if query.elderly_in_group:
        threshold = 3500
    elif query.group_composition.value == "family":
        threshold = 3000
    safety = max(0.0, min(1.0, 1.0 - (max_alt / threshold) * 0.5))

    # Weather: seasonal accessibility for travel month
    open_count = sum(1 for d in dests if d.season_open[query.travel_month - 1])
    weather = open_count / len(dests) if dests else 0.5

    # Budget fit
    budget_fit = min(1.0, candidate.estimated_cost / max(1, query.budget_pkr))
    if candidate.estimated_cost > query.budget_pkr:
        budget_fit = max(0.0, 1.0 - (candidate.estimated_cost - query.budget_pkr) / query.budget_pkr)

    # Trip score: weighted blend
    trip_score = safety * 0.35 + weather * 0.30 + budget_fit * 0.35

    return {
        "safety": round(safety, 2),
        "weather": round(weather, 2),
        "budget_fit": round(budget_fit, 2),
        "trip_score": round(trip_score, 2),
    }


@router.post("/preview")
def plan_preview(request: PlanRequest):
    """Lightweight preview — recommender only, no debate.

    Returns the top candidate + rough scores so the planning canvas can
    show a live preview without running the full 16-LLM-call debate.
    """
    try:
        query = UserQuery.model_validate(request.query)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid query: {exc}") from exc

    try:
        candidates, _ = recommend_with_trace(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preview failed: {exc}") from exc

    if not candidates:
        return {"trip_id": None, "top": None, "candidates": [], "rough_scores": None}

    top = candidates[0]
    return {
        "trip_id": None,
        "top": _serialize(top),
        "candidates": _serialize(candidates[:3]),
        "rough_scores": _heuristic_scores(top, query),
    }


@router.post("", response_model=PlanResponse)
def plan_trip(request: PlanRequest):
    """Generate route candidates and run the agent debate."""
    try:
        query = UserQuery.model_validate(request.query)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid query: {exc}") from exc

    try:
        candidates, rec_trace = recommend_with_trace(query)
        debate_result = run_debate(query, candidates, use_full_llm=request.full_llm_mode)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Planning failed: {exc}") from exc

    return {
        "trip_id": f"trip_{uuid.uuid4().hex[:12]}",
        "query": _serialize(query),
        "candidates": _serialize(candidates),
        "recommendation_trace": _serialize(rec_trace),
        "debate_result": _serialize(debate_result),
    }


@router.post("/stream")
def plan_trip_stream(request: PlanRequest):
    """Stream debate progress via Server-Sent Events."""
    try:
        query = UserQuery.model_validate(request.query)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid query: {exc}") from exc

    def event_stream():
        try:
            candidates, rec_trace = recommend_with_trace(query)
            # Send a single initial event with candidates + trace so the UI can
            # render the map while agents debate.
            initial = {
                "type": "recommendation_done",
                "trip_id": f"trip_{uuid.uuid4().hex[:12]}",
                "query": _serialize(query),
                "candidates": _serialize(candidates),
                "recommendation_trace": _serialize(rec_trace),
            }
            yield f"data: {json.dumps(initial)}\n\n"

            for event in run_debate_stream(query, candidates, use_full_llm=request.full_llm_mode):
                yield f"data: {json.dumps(_serialize(event))}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
