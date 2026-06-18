"""
File-backed JSON cache for any expensive call (LLM, weather, RAG embeddings).

Two env flags govern behavior:

    MANZIL_USE_CACHE=1   read from cache, fall through to live call on miss (default)
    MANZIL_DEMO_MODE=1   read from cache only — raise CacheMiss on miss
                         (used on demo day so a flaky network can't kill the demo)

Storage layout:

    <MANZIL_CACHE_DIR>/
        llm.json
        weather.json
        ...

Each namespace is a single JSON file mapping cache_key -> value. We rewrite the
whole file on each write — fine at our scale (low hundreds of entries). If we
ever hit a concurrency problem we'll add a file lock.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional


class CacheMiss(Exception):
    """Raised when MANZIL_DEMO_MODE=1 and the lookup misses."""


def _cache_dir() -> Path:
    raw = os.environ.get("MANZIL_CACHE_DIR", ".manzil_cache")
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() in {"1", "true", "True", "yes"}


def is_enabled() -> bool:
    """Cache reads are enabled (always true in demo mode regardless of USE_CACHE)."""
    return _flag("MANZIL_USE_CACHE", "1") or is_demo_mode()


def is_demo_mode() -> bool:
    return _flag("MANZIL_DEMO_MODE", "0")


def stable_key(payload: Any) -> str:
    """
    Compute a stable cache key from any JSON-serializable payload.

    For an LLM call you would call e.g.
        stable_key({"model": "...", "prompt": "...", "temperature": 0.2})
    """
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


class _NamespaceStore:
    """In-memory mirror of one JSON file. Loaded lazily, written on every set."""

    def __init__(self, namespace: str):
        self.path = _cache_dir() / f"{namespace}.json"
        self._data: Optional[Dict[str, Any]] = None
        self._lock = RLock()

    def _load(self) -> Dict[str, Any]:
        if self._data is not None:
            return self._data
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._data = {}
        else:
            self._data = {}
        return self._data

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._load().get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._load()
            data[key] = value
            tmp = self.path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            tmp.replace(self.path)


# Module-level registry so each namespace is loaded once per process.
_STORES: Dict[str, _NamespaceStore] = {}
_REGISTRY_LOCK = RLock()


def _store(namespace: str) -> _NamespaceStore:
    with _REGISTRY_LOCK:
        if namespace not in _STORES:
            _STORES[namespace] = _NamespaceStore(namespace)
        return _STORES[namespace]


def get(namespace: str, key: str) -> Optional[Any]:
    """Read from cache. Returns None on miss (unless demo mode -> raises)."""
    if not is_enabled():
        if is_demo_mode():
            raise CacheMiss(f"demo mode: lookup miss in '{namespace}' for key {key}")
        return None
    hit = _store(namespace).get(key)
    if hit is None and is_demo_mode():
        raise CacheMiss(f"demo mode: lookup miss in '{namespace}' for key {key}")
    return hit


def set(namespace: str, key: str, value: Any) -> None:
    """Write to cache. No-op in demo mode (we should never be doing live calls)."""
    if is_demo_mode():
        # Defensive — caller should not be calling set() in demo mode.
        return
    _store(namespace).set(key, value)


def clear(namespace: Optional[str] = None) -> None:
    """Wipe a namespace (or all). Test-only."""
    with _REGISTRY_LOCK:
        if namespace is None:
            for ns in list(_STORES.keys()):
                _STORES[ns]._data = {}
                if _STORES[ns].path.exists():
                    _STORES[ns].path.unlink()
            _STORES.clear()
        elif namespace in _STORES:
            _STORES[namespace]._data = {}
            if _STORES[namespace].path.exists():
                _STORES[namespace].path.unlink()
            del _STORES[namespace]


__all__ = ["CacheMiss", "stable_key", "get", "set", "clear", "is_enabled", "is_demo_mode"]
