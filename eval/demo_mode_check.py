"""
Demo mode cache check — verifies every expected cache key is present.

Run once before demo day, after `python scripts/seed_caches.py` has
completed. If any key is missing, the demo will hit cache misses and
the build should fail.

Usage:
    python eval/demo_mode_check.py

Exit code:
    0 — all keys present
    1 — one or more keys missing
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List

_CACHE_DIR = Path(os.environ.get("MANZIL_CACHE_DIR", ".manzil_cache"))


def _check_namespace(name: str, expected_min_entries: int) -> List[str]:
    path = _CACHE_DIR / f"{name}.json"
    if not path.exists():
        return [f"  MISSING namespace file: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"  CORRUPT {name}: {exc}"]

    n = len(data)
    if n == 0:
        return [f"  EMPTY {name}: 0 entries"]
    if n < expected_min_entries:
        return [f"  LOW {name}: {n} entries (expected >={expected_min_entries})"]
    return []


def check() -> int:
    errors: List[str] = []

    if not _CACHE_DIR.exists():
        errors.append(f"CACHE DIR NOT FOUND: {_CACHE_DIR}")
        errors.append("  Run `python scripts/seed_caches.py` first.")
    else:
        # Check llm cache — expect entries for the 6-step demo flow
        errors.extend(_check_namespace("llm", expected_min_entries=5))
        errors.extend(_check_namespace("weather", expected_min_entries=3))
        errors.extend(_check_namespace("embedding", expected_min_entries=1))

    if errors:
        print("Demo mode check: FAILED")
        for e in errors:
            print(e)
        return 1

    print("Demo mode check: PASSED")
    print(f"  llm.json:     OK (>=5 entries)")
    print(f"  weather.json: OK (>=3 entries)")
    print(f"  embedding.json: OK (>=1 entry)")
    return 0


def main() -> None:
    sys.exit(check())


if __name__ == "__main__":
    main()
