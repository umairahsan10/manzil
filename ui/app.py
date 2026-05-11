"""
Manzil — Streamlit entrypoint.

Run from the project root:

    streamlit run ui/app.py

This file is the landing page (env state + 3 healthchecks). The Plan page is
auto-discovered from `ui/pages/plan.py` by Streamlit's multipage system and
appears in the sidebar.
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

# Force-refresh .env on every page load so key changes are picked up
# without restarting the Streamlit server.
load_dotenv(_ROOT / ".env", override=True)

import streamlit as st  # noqa: E402

from manzil import __version__  # noqa: E402
from manzil import llm  # noqa: E402
from manzil.agents.base import is_full_llm_mode  # noqa: E402
from manzil.tools import cache, weather_api  # noqa: E402

st.set_page_config(page_title="Manzil", page_icon="🏔️", layout="wide")

st.title("Manzil")
st.caption(
    f"Multi-agent travel planner for northern Pakistan · v{__version__} · "
    "Phase 4 — UI Polish + Memory Loop"
)
st.write(
    "Pick **Plan** from the left sidebar to start a trip, or **Feedback** to "
    "rate a past recommendation. This page shows the system healthchecks — "
    "useful when something is misbehaving."
)

# ---------------------------------------------------------------------------
# Environment row
# ---------------------------------------------------------------------------

env_cols = st.columns(5)
env_cols[0].metric("USE_CACHE", "on" if cache.is_enabled() else "off")
env_cols[1].metric("DEMO_MODE", "on" if cache.is_demo_mode() else "off")
env_cols[2].metric(
    "AGENT_MODE",
    "Full LLM" if is_full_llm_mode() else "Efficient",
)

# Key rotation status
keys = llm.get_key_states()
if keys:
    active = sum(1 for ks in keys if ks.available)
    env_cols[3].metric("API_KEYS", f"{active}/{len(keys)} active")
else:
    env_cols[3].metric("API_KEYS", "not configured")

env_cols[4].metric("CACHE_DIR", os.environ.get("MANZIL_CACHE_DIR", ".manzil_cache"))

# Per-key quota bars
if keys:
    st.caption("API Key quotas (20 calls/day per key)")
    key_cols = st.columns(min(len(keys), 5))
    for i, ks in enumerate(keys):
        with key_cols[i % len(key_cols)]:
            used_today = ks.calls_today()
            remaining = max(0, 20 - used_today)
            st.progress(remaining / 20.0, text=f"Key {i+1}: {remaining}/20 today")

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

# --- LLM ---
with col_llm:
    st.markdown("**DeepSeek V4 Pro**")
    if not keys and not cache.is_demo_mode():
        st.warning(
            "No GEMINI_API_KEYS found. Copy `.env.example` to `.env` and add keys, "
            "or set MANZIL_DEMO_MODE=1 to run cache-only."
        )
    else:
        ok, msg = llm.healthcheck()
        if ok:
            st.success(f"OK — {msg}")
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

st.divider()
st.caption(
    "Phase 4 status: full UI polish (map, scorecard heatmap, debate trace, "
    "dissent/why-not, side-by-side replanning) + memory loop (feedback → case base)."
)
