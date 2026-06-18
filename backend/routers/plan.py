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
