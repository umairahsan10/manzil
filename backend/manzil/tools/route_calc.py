"""
Route calculator — deterministic drive-time lookup.

Pure Python over `data/road_knowledge.json`. No LLM. No API calls.

Exposes:
    drive_time(from_id, to_id) -> float   # hours
    route_segments(origin, destinations) -> List[dict]
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from manzil.data_loader import load_road_knowledge


def drive_time(from_id: str, to_id: str) -> float:
    """Return drive time in hours for a single segment."""
    rk = load_road_knowledge()
    segments = rk.get("segments", {})
    key = f"{from_id}__{to_id}"
    seg = segments.get(key)
    if seg is None:
        return 0.0
    return float(seg.get("drive_time_hours", 0.0))


def route_segments(origin: str, destinations: List[str]) -> List[Dict]:
    """
    Return a list of segment dicts for the full route.
    Each dict has: leg_key, from_id, to_id, drive_time_hours, distance_km, via.
    """
    rk = load_road_knowledge()
    segments = rk.get("segments", {})
    out = []
    prev = origin
    for dest in destinations:
        key = f"{prev}__{dest}"
        seg = segments.get(key)
        if seg is None:
            out.append(
                {
                    "leg_key": key,
                    "from_id": prev,
                    "to_id": dest,
                    "drive_time_hours": 0.0,
                    "distance_km": 0,
                    "via": [],
                    "missing": True,
                }
            )
        else:
            out.append(
                {
                    "leg_key": key,
                    "from_id": prev,
                    "to_id": dest,
                    "drive_time_hours": float(seg.get("drive_time_hours", 0.0)),
                    "distance_km": int(seg.get("distance_km", 0)),
                    "via": seg.get("via", []),
                    "missing": False,
                }
            )
        prev = dest
    return out


def passes_on_route(origin: str, destinations: List[str]) -> List[Dict]:
    """
    Return a list of mountain passes / tunnels that the route traverses,
    based on the 'via' field of each segment.
    """
    rk = load_road_knowledge()
    passes_db = rk.get("passes", {})
    segs = route_segments(origin, destinations)

    seen = set()
    out = []
    for seg in segs:
        for via_point in seg.get("via", []):
            for pass_id, pass_data in passes_db.items():
                if via_point == pass_id and pass_id not in seen:
                    seen.add(pass_id)
                    out.append({"pass_id": pass_id, **pass_data})
    return out


def landslide_risk_for_month(origin: str, destinations: List[str], month: int) -> float:
    """
    Aggregate landslide risk across the route for the given month.
    Returns the MAX risk among all segments (conservative).
    Month is 1-12.
    """
    rk = load_road_knowledge()
    segments = rk.get("segments", {})
    month_key = str(month - 1)  # JSON uses 0-based index
    max_risk = 0.0

    prev = origin
    for dest in destinations:
        key = f"{prev}__{dest}"
        seg = segments.get(key)
        if seg is not None:
            risk_map = seg.get("landslide_risk_by_month", {})
            risk = risk_map.get(month_key, 0.0)
            max_risk = max(max_risk, risk)
        prev = dest

    return max_risk


def total_drive_time(origin: str, destinations: List[str]) -> float:
    """Sum of drive times for all segments."""
    return sum(s["drive_time_hours"] for s in route_segments(origin, destinations))


def max_single_leg_drive_time(origin: str, destinations: List[str]) -> float:
    """Longest single segment drive time."""
    segs = route_segments(origin, destinations)
    if not segs:
        return 0.0
    return max(s["drive_time_hours"] for s in segs)


__all__ = [
    "drive_time",
    "route_segments",
    "passes_on_route",
    "landslide_risk_for_month",
    "total_drive_time",
    "max_single_leg_drive_time",
]
