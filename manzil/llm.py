"""
Gemini client wrapper.

Two model tiers are exposed:
    Model.FLASH_LITE   — for the 5 specialist agents (1 call per agent per candidate)
    Model.FLASH        — for the Orchestrator (1 deeper synthesis call per debate)

All calls go through the cache. In demo mode, a miss raises `CacheMiss` so the
demo cannot accidentally hit the network.

The `complete_json(...)` helper requests JSON, parses it against a Pydantic
schema, retries once with a stricter prompt if parsing fails, then raises
`LLMParseError` so the caller can fall back to a deterministic argument with
`confidence=0.0`.
"""

from __future__ import annotations

import json
import logging
import os
import re
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from manzil.tools import cache

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class Model(str, Enum):
    FLASH_LITE = "gemini-2.5-flash-lite"
    FLASH = "gemini-2.5-flash"


class LLMError(Exception):
    pass


class LLMParseError(LLMError):
    """Raised when JSON output cannot be parsed against the requested schema."""


# ---------------------------------------------------------------------------
# Lazy client init — google-generativeai is only imported when first needed
# so demo mode (cache-only) does not require the API key to be set.
# ---------------------------------------------------------------------------


_CLIENT_READY = False


def _ensure_client() -> None:
    global _CLIENT_READY
    if _CLIENT_READY:
        return
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise LLMError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in, "
            "or run with MANZIL_DEMO_MODE=1 to use the cache only."
        )
    import google.generativeai as genai  # noqa: WPS433 (deliberate lazy import)

    genai.configure(api_key=api_key)
    _CLIENT_READY = True


def _cache_key(model: Model, prompt: str, temperature: float, system: Optional[str]) -> str:
    return cache.stable_key(
        {
            "model": model.value,
            "prompt": prompt,
            "temperature": round(temperature, 3),
            "system": system or "",
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
) -> str:
    """Return raw text from Gemini, cached by (model, prompt, temperature, system)."""
    key = _cache_key(model, prompt, temperature, system)

    cached = cache.get("llm", key)
    if cached is not None:
        return cached["text"]

    if cache.is_demo_mode():
        raise cache.CacheMiss(f"demo mode: no cached LLM response for key {key}")

    _ensure_client()
    import google.generativeai as genai  # noqa: WPS433

    config: Dict[str, Any] = {"temperature": temperature}
    gen_model = genai.GenerativeModel(
        model_name=model.value,
        system_instruction=system,
        generation_config=config,
    )
    resp = gen_model.generate_content(prompt)
    text = (resp.text or "").strip()

    cache.set("llm", key, {"text": text, "model": model.value})
    return text


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
    parsed, _ = _try_parse(prompt, schema, model=model, temperature=temperature, system=system)
    if parsed is not None:
        return parsed

    # Retry with a stricter prompt
    stricter = (
        prompt
        + "\n\nIMPORTANT: Reply with ONLY a single JSON object matching the schema. "
        "No markdown, no commentary, no fences. Begin your response with { and end with }."
    )
    parsed, raw = _try_parse(stricter, schema, model=model, temperature=temperature, system=system)
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
) -> tuple[Optional[T], str]:
    raw = complete(prompt, model=model, temperature=temperature, system=system)
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


def healthcheck() -> tuple[bool, str]:
    """
    One trivial round-trip used by the Streamlit healthcheck row.
    Returns (ok, message). Cached after the first successful call.
    """
    try:
        text = complete(
            "Reply with the single word: ok",
            model=Model.FLASH_LITE,
            temperature=0.0,
        )
        return True, text or "(empty)"
    except Exception as exc:  # noqa: BLE001 — UI surface
        return False, f"{type(exc).__name__}: {exc}"


__all__ = ["Model", "LLMError", "LLMParseError", "complete", "complete_json", "healthcheck"]
