"""
OpenAI-compatible LLM client wrapper with multi-key rotation and per-key
rate limiting.

Configured for DeepSeek V4 Pro via opencode.ai by default, but works with
any OpenAI-compatible endpoint (set LLM_API_BASE_URL).

Two model tiers are exposed (both map to the same underlying model):
    Model.FLASH_LITE   — for the 5 specialist agents
    Model.FLASH        — for the Orchestrator synthesis call

All calls go through the cache. In demo mode, a miss raises `CacheMiss` so the
demo cannot accidentally hit the network.

The `complete_json(...)` helper requests JSON, parses it against a Pydantic
schema, retries once with a stricter prompt if parsing fails, then raises
`LLMParseError` so the caller can fall back to a deterministic argument with
`confidence=0.0`.

Key rotation:
    - Set LLM_API_KEYS=key1,key2,key3 (comma-separated) in .env
    - Falls back to legacy GEMINI_API_KEYS / GEMINI_API_KEY for smooth migration
    - Each key has its own RPM and RPD rate-limit window
    - On 429 from key A, immediately retries key B
    - On 403/401, marks key unavailable permanently
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from manzil.tools import cache

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1"
_DEFAULT_MODEL = "deepseek-v4-pro"

_LLM_BASE_URL = os.environ.get("LLM_API_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
_LLM_MODEL = os.environ.get("LLM_MODEL", _DEFAULT_MODEL)

_RPM_LIMIT = int(os.environ.get("MANZIL_LLM_RPM", os.environ.get("MANZIL_GEMINI_RPM", "100")))
_RPD_LIMIT = int(os.environ.get("MANZIL_LLM_RPD", os.environ.get("MANZIL_GEMINI_RPD", "1000")))
_MINUTE_WINDOW = 60.0
_DAY_WINDOW = 86400.0


class Model(str, Enum):
    FLASH_LITE = _LLM_MODEL
    FLASH = _LLM_MODEL


class LLMError(Exception):
    pass


class LLMParseError(LLMError):
    """Raised when JSON output cannot be parsed against the requested schema."""


# ---------------------------------------------------------------------------
# Per-key rate-limit state
# ---------------------------------------------------------------------------


class _KeyState:
    """Tracks rate-limit state for a single API key."""

    def __init__(self, key: str, index: int) -> None:
        self.key = key
        self.index = index
        self.minute_calls: deque[float] = deque()
        self.day_calls: deque[float] = deque()
        self.lock = threading.Lock()
        self.available = True
        self.last_error: Optional[str] = None

    def _clean_windows(self, now: float) -> None:
        while self.minute_calls and self.minute_calls[0] < now - _MINUTE_WINDOW:
            self.minute_calls.popleft()
        while self.day_calls and self.day_calls[0] < now - _DAY_WINDOW:
            self.day_calls.popleft()

    def can_call(self) -> bool:
        if not self.available:
            return False
        with self.lock:
            now = time.time()
            self._clean_windows(now)
            return (
                len(self.minute_calls) < _RPM_LIMIT
                and len(self.day_calls) < _RPD_LIMIT
            )

    def record_call(self) -> None:
        with self.lock:
            now = time.time()
            self._clean_windows(now)
            self.minute_calls.append(now)
            self.day_calls.append(now)

    def mark_unavailable(self, reason: str) -> None:
        self.available = False
        self.last_error = reason

    def calls_today(self) -> int:
        with self.lock:
            now = time.time()
            self._clean_windows(now)
            return len(self.day_calls)


_KEY_STATES: List[_KeyState] = []
_LAST_KEY_INDEX = -1
_KEYS_LOCK = threading.Lock()
_KEYS_INITIALIZED = False


def _parse_api_keys() -> List[str]:
    """Parse LLM_API_KEYS or fall back to legacy GEMINI_API_KEYS / GEMINI_API_KEY."""
    multi = os.environ.get("LLM_API_KEYS", "").strip()
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    # Legacy fallback for smooth migration
    multi = os.environ.get("GEMINI_API_KEYS", "").strip()
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    single = os.environ.get("GEMINI_API_KEY", "").strip()
    return [single] if single else []


def _ensure_keys() -> None:
    """Lazy-init key states."""
    global _KEYS_INITIALIZED, _KEY_STATES
    if _KEYS_INITIALIZED:
        return
    with _KEYS_LOCK:
        if _KEYS_INITIALIZED:
            return
        keys = _parse_api_keys()
        _KEY_STATES = [_KeyState(k, i) for i, k in enumerate(keys)]
        _KEYS_INITIALIZED = True
        log.info("Initialized %d API key(s)", len(_KEY_STATES))


def get_key_states() -> List[_KeyState]:
    """Return current key states (for UI display)."""
    _ensure_keys()
    return list(_KEY_STATES)


# ---------------------------------------------------------------------------
# Key rotation + retry
# ---------------------------------------------------------------------------


def _pick_available_key() -> _KeyState:
    """Round-robin across available keys. Raises if all exhausted."""
    global _LAST_KEY_INDEX
    _ensure_keys()
    with _KEYS_LOCK:
        if not _KEY_STATES:
            raise LLMError("No API keys configured. Set LLM_API_KEYS.")

        for offset in range(len(_KEY_STATES)):
            idx = (_LAST_KEY_INDEX + 1 + offset) % len(_KEY_STATES)
            ks = _KEY_STATES[idx]
            if ks.can_call():
                _LAST_KEY_INDEX = idx
                return ks

        now = time.time()
        earliest_day_reset = min(
            (ks.day_calls[0] + _DAY_WINDOW if ks.day_calls else now)
            for ks in _KEY_STATES
        )
        earliest_min_reset = min(
            (ks.minute_calls[0] + _MINUTE_WINDOW if ks.minute_calls else now)
            for ks in _KEY_STATES
        )
        sleep_seconds = min(earliest_day_reset, earliest_min_reset) - now
        raise LLMError(
            f"All {len(_KEY_STATES)} API keys exhausted. "
            f"Retry after {max(0, sleep_seconds):.0f}s."
        )


# ---------------------------------------------------------------------------
# OpenAI client init
# ---------------------------------------------------------------------------

_CONFIGURED_KEY: Optional[str] = None
_CLIENT_LOCK = threading.Lock()


def _get_client(api_key: str) -> Any:
    """Build an OpenAI client for the given key."""
    global _CONFIGURED_KEY, _client
    if _CONFIGURED_KEY == api_key:
        return _client
    with _CLIENT_LOCK:
        if _CONFIGURED_KEY == api_key:
            return _client
        from openai import OpenAI  # noqa: WPS433

        client = OpenAI(
            base_url=_LLM_BASE_URL,
            api_key=api_key,
            timeout=60.0,
        )
        _client = client
        _CONFIGURED_KEY = api_key
        return client


# Module-level client cache
_client: Any = None


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


def _cache_key(
    model: Model,
    prompt: str,
    temperature: float,
    system: Optional[str],
    json_mode: bool = False,
) -> str:
    from manzil.agents.base import is_full_llm_mode

    mode = "full" if is_full_llm_mode() else "eff"
    return cache.stable_key(
        {
            "model": model.value,
            "prompt": prompt,
            "temperature": round(temperature, 3),
            "system": system or "",
            "mode": mode,
            "json_mode": json_mode,
        }
    )


# ---------------------------------------------------------------------------
# Plain text completion
# ---------------------------------------------------------------------------


def complete(
    prompt: str,
    *,
    model: Model = Model.FLASH_LITE,
    temperature: float = 0.2,
    system: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """Return raw text from the LLM, cached by (model, prompt, temperature, system, mode)."""
    key = _cache_key(model, prompt, temperature, system, json_mode=json_mode)

    cached = cache.get("llm", key)
    if cached is not None:
        return cached["text"]

    if cache.is_demo_mode():
        raise cache.CacheMiss(f"demo mode: no cached LLM response for key {key}")

    # Retry up to 3 times when rate-limited (waiting for window reset)
    key_exhausted_retries = 3
    for _ in range(key_exhausted_retries):
        try:
            ks = _pick_available_key()
        except LLMError as exc:
            # All keys exhausted — extract wait time and retry
            msg = str(exc)
            retry_after = 1.0
            # Parse "Retry after Xs." from the error message
            import re as _re
            m = _re.search(r"Retry after (\d+)s", msg)
            if m:
                retry_after = max(float(m.group(1)), 1.0)
            log.warning("All keys exhausted, waiting %.0fs before retry…", retry_after)
            time.sleep(retry_after + 0.5)
            continue

        try:
            client = _get_client(ks.key)

            messages: List[Dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            api_kwargs: Dict[str, Any] = {
                "model": model.value,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2048,
            }
            if json_mode:
                api_kwargs["response_format"] = {"type": "json_object"}

            try:
                resp = client.chat.completions.create(**api_kwargs)
            except Exception as inner_exc:
                # Retry without response_format only for schema-rejection errors
                if json_mode and api_kwargs.get("response_format"):
                    inner_name = type(inner_exc).__name__
                    inner_msg = str(inner_exc)
                    if "response_format" in inner_msg or "BadRequestError" in inner_name:
                        api_kwargs.pop("response_format", None)
                        log.warning(
                            "JSON mode not supported by endpoint, falling back to prompt-only"
                        )
                        resp = client.chat.completions.create(**api_kwargs)
                    else:
                        raise
                else:
                    raise

            text = (resp.choices[0].message.content or "").strip()

            ks.record_call()
            cache.set("llm", key, {"text": text, "model": model.value})
            return text
        except Exception as exc:  # noqa: BLE001
            exc_name = type(exc).__name__
            msg = str(exc)
            if "429" in msg or "RateLimitError" in exc_name:
                ks.mark_unavailable(f"429")
                log.warning("Key %d hit 429, trying next…", ks.index)
                continue
            if "401" in msg or "403" in msg or "AuthenticationError" in exc_name or "PermissionDeniedError" in exc_name:
                ks.mark_unavailable(f"{msg}")
                log.warning("Key %d auth error (%s), marking unavailable", ks.index, msg)
                continue
            # Real error — don't retry with other keys
            raise

    raise LLMError(f"All API keys exhausted after {key_exhausted_retries} retries.")


# ---------------------------------------------------------------------------
# JSON-structured completion with schema validation + retry-once-then-fallback
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> str:
    """Strip ```json fences if present; otherwise return the raw text."""
    m = _JSON_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def complete_json(
    prompt: str,
    schema: Type[T],
    *,
    model: Model = Model.FLASH_LITE,
    temperature: float = 0.2,
    system: Optional[str] = None,
) -> T:
    """
    Ask the LLM for JSON matching `schema`. Parse it. Retry once with a
    stricter prompt if parsing fails. Raise `LLMParseError` if it fails twice.
    """
    parsed, _ = _try_parse(
        prompt, schema, model=model, temperature=temperature, system=system, json_mode=True
    )
    if parsed is not None:
        return parsed

    stricter = (
        prompt
        + "\n\nIMPORTANT: Reply with ONLY a single JSON object matching the schema. "
        "No markdown, no commentary, no fences. Begin your response with { and end with }."
    )
    parsed, raw = _try_parse(
        stricter, schema, model=model, temperature=temperature, system=system, json_mode=True
    )
    if parsed is not None:
        return parsed

    raise LLMParseError(
        f"Could not parse {schema.__name__} from LLM output after one retry. "
        f"Raw (truncated): {raw[:300]!r}"
    )


def _try_parse(
    prompt: str,
    schema: Type[T],
    *,
    model: Model,
    temperature: float,
    system: Optional[str],
    json_mode: bool = False,
) -> tuple[Optional[T], str]:
    raw = complete(prompt, model=model, temperature=temperature, system=system, json_mode=json_mode)
    body = _extract_json(raw)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        log.warning("LLM JSON parse failed for %s", schema.__name__)
        return None, raw
    try:
        return schema.model_validate(data), raw
    except ValidationError:
        log.warning("LLM schema validation failed for %s", schema.__name__)
        return None, raw


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


def healthcheck() -> tuple[bool, str]:
    """
    Lightweight healthcheck. Reports key count and availability
    without burning API quota.
    """
    keys = _parse_api_keys()
    if not keys:
        return False, "No API keys configured"

    _ensure_keys()
    active = sum(1 for ks in _KEY_STATES if ks.available)
    return True, f"{active}/{len(keys)} keys active · {_LLM_MODEL} @ {_LLM_BASE_URL}"


__all__ = [
    "Model",
    "LLMError",
    "LLMParseError",
    "complete",
    "complete_json",
    "healthcheck",
    "get_key_states",
]
