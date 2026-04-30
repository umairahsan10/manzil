"""
Single-file loader for the JSON knowledge bases under `data/`.

`@lru_cache(maxsize=1)` means each file is parsed once per process. To
trigger a re-read (e.g., after writing a new `CaseBaseEntry` from the
feedback loop in Phase 4), call `<loader>.cache_clear()`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from manzil.schemas import CaseBaseEntry, Destination

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def data_dir() -> Path:
    return _DATA_DIR


@lru_cache(maxsize=1)
def load_destinations() -> Dict[str, Destination]:
    """Returns id → Destination. Cached for the process lifetime."""
    with (_DATA_DIR / "destinations.json").open("r", encoding="utf-8") as f:
        items = json.load(f)
    return {item["id"]: Destination.model_validate(item) for item in items}


@lru_cache(maxsize=1)
def load_costs() -> Dict[str, Any]:
    with (_DATA_DIR / "costs.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_road_knowledge() -> Dict[str, Any]:
    with (_DATA_DIR / "road_knowledge.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_safety_knowledge() -> Dict[str, Any]:
    with (_DATA_DIR / "safety_knowledge.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def load_case_base() -> List[CaseBaseEntry]:
    """
    Not @lru_cache'd because Phase 4's feedback loop appends to this file
    during a session. The recommender's CBR step calls this on every query.
    """
    path = _DATA_DIR / "case_base.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        items = json.load(f)
    return [CaseBaseEntry.model_validate(item) for item in items]


__all__ = [
    "data_dir",
    "load_destinations",
    "load_costs",
    "load_road_knowledge",
    "load_safety_knowledge",
    "load_case_base",
]
