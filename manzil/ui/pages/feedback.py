"""
Feedback page (Streamlit auto-discovered).

Post-trip feedback form: rating, tag multi-select.
After submit, render confirmation and a shortcut to re-run a similar query.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import streamlit as st  # noqa: E402

from manzil.memory.feedback import VALID_TAGS, get_feedback_stats, submit_feedback  # noqa: E402

st.set_page_config(page_title="Manzil — Feedback", page_icon="⭐", layout="wide")

st.title("Trip feedback")
st.caption(
    "Rate your trip so Manzil can learn. Your feedback enters the case base "
    "and influences recommendations for similar travellers."
)

# ---------------------------------------------------------------------------
# Feedback form
# ---------------------------------------------------------------------------

with st.form("feedback_form"):
    st.subheader("How was your trip?")

    rating = st.slider(
        "Overall rating",
        min_value=1.0,
        max_value=5.0,
        value=4.0,
        step=0.5,
        help="1 = terrible, 5 = perfect",
    )

    tags = st.multiselect(
        "What stood out?",
        options=sorted(VALID_TAGS),
        default=[],
        help="Select all that apply",
    )

    submitted = st.form_submit_button("Submit feedback", use_container_width=True)

# ---------------------------------------------------------------------------
# Handle submission
# ---------------------------------------------------------------------------

if submitted:
    # We need the last query and winner from session state (set by plan page)
    last_query = st.session_state.get("last_query")
    last_result = st.session_state.get("last_result")

    if not last_query or not last_result:
        st.error(
            "No recent trip found. Please go to the Plan page, submit a query, "
            "and then return here to rate the result."
        )
    else:
        winner = last_result.winner
        if not winner:
            st.warning(
                "The last recommendation had no winner (all candidates were blocked). "
                "Feedback is still welcome, but it won't be used for case-base learning."
            )
            # Store a placeholder so the user feels heard
            st.session_state["feedback_submitted"] = True
        else:
            travel_mode_strs = [tm.value for tm in winner.travel_modes]
            entry = submit_feedback(
                query=last_query,
                winner_route=winner.destinations,
                travel_modes=travel_mode_strs,
                rating=rating,
                tags=tags,
            )
            st.session_state["feedback_submitted"] = True
            st.session_state["feedback_entry_id"] = entry.case_id

            st.success(
                f"Feedback submitted! Entry ID: `{entry.case_id}`. "
                f"It is now in the case base and will influence the next recommendation."
            )

# ---------------------------------------------------------------------------
# Post-submit actions
# ---------------------------------------------------------------------------

if st.session_state.get("feedback_submitted"):
    st.divider()
    st.markdown("**What next?**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Try a similar query now", use_container_width=True):
            st.switch_page("manzil/ui/pages/plan.py")
    with col2:
        if st.button("Clear and submit another", use_container_width=True):
            st.session_state["feedback_submitted"] = False
            st.session_state.pop("feedback_entry_id", None)
            st.rerun()

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

st.divider()
stats = get_feedback_stats()
if stats["count"] == 0:
    st.caption("No real-user feedback yet. Be the first!")
else:
    st.markdown("##### Feedback so far")
    cols = st.columns(3)
    cols[0].metric("Submissions", stats["count"])
    cols[1].metric("Average rating", f"{stats['avg_rating']:.1f} / 5.0")
    if stats["top_tags"]:
        top_tag_str = ", ".join(f"{tag} ({cnt})" for tag, cnt in stats["top_tags"])
        cols[2].metric("Top tags", top_tag_str)
