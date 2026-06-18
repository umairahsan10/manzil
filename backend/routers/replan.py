"""Replanning endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/replan", tags=["replan"])


@router.post("")
def replan_trip():
    return {"detail": "Not implemented yet"}
