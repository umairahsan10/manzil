"""
Manzil — Streamlit entrypoint.

Run from the project root:

    streamlit run ui/app.py

In Phase 0 this is a healthcheck-only page proving:
    - schemas import cleanly
    - the LLM client can reach Gemini (or replay from cache)
    - the Open-Meteo wrapper can reach the API (or replay from cache)
    - the cache flags are wired correctly
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the project root importable when Streamlit runs `ui/app.py` directly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import streamlit as st  # noqa: E402

from manzil import __version__  # noqa: E402
from manzil import llm  # noqa: E402
from manzil.tools import cache, weather_api  # noqa: E402

st.set_page_config(page_title="Manzil", page_icon="🏔️", layout="wide")

st.title("Manzil")
st.caption(
    f"Multi-agent travel planner for northern Pakistan · v{__version__} · "
    "Phase 0 — Foundations"
)

# ---------------------------------------------------------------------------
# Environment row
# ---------------------------------------------------------------------------

env_cols = st.columns(4)
env_cols[0].metric("USE_CACHE", "on" if cache.is_enabled() else "off")
env_cols[1].metric("DEMO_MODE", "on" if cache.is_demo_mode() else "off")
env_cols[2].metric(
    "GEMINI_API_KEY",
    "set" if os.environ.get("GEMINI_API_KEY") else "missing",
)
env_cols[3].metric("CACHE_DIR", os.environ.get("MANZIL_CACHE_DIR", ".manzil_cache"))

# ---------------------------------------------------------------------------
# Healthcheck row
# ---------------------------------------------------------------------------

st.subheader("Healthchecks")
st.caption(
    "Run on first page load. Successful calls are cached, so refreshing should "
    "be instant and free."
)

col_schemas, col_llm, col_weather = st.columns(3)

# --- Schemas ---
with col_schemas:
    st.markdown("**Schemas**")
    try:
        from manzil import schemas  # noqa: F401

        st.success("OK — schemas import cleanly")
    except Exception as exc:  # noqa: BLE001 — UI surface
        st.error(f"FAILED — {type(exc).__name__}: {exc}")

# --- Gemini ---
with col_llm:
    st.markdown("**Gemini (Flash-Lite)**")
    if not os.environ.get("GEMINI_API_KEY") and not cache.is_demo_mode():
        st.warning(
            "No GEMINI_API_KEY found. Copy `.env.example` to `.env` and add a key, "
            "or set MANZIL_DEMO_MODE=1 to run cache-only."
        )
    else:
        ok, msg = llm.healthcheck()
        if ok:
            st.success(f"OK — round-trip reply: `{msg}`")
        else:
            st.error(f"FAILED — {msg}")

# --- Open-Meteo ---
with col_weather:
    st.markdown("**Open-Meteo**")
    ok, msg = weather_api.healthcheck()
    if ok:
        st.success(f"OK — Karimabad sample: {msg}")
    else:
        st.error(f"FAILED — {msg}")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "Next: Phase 1 wires the form, stub recommender, and one real agent end-to-end. "
    "If any healthcheck above is red we should fix it before continuing."
)
