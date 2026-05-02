"""
Plan page (Streamlit auto-discovered).

The form builds a `UserQuery`. The recommender returns 3 stub candidates.
The LangGraph debate runs through 5 agents (1 real, 4 stubs in Phase 1) and
the Orchestrator picks a winner.

Phase 1 surfaces:
    - 3 candidate preview cards (label, destinations, cost, axis tags)
    - Full day-by-day plan for the winner
    - 5 x 3 scorecard table
    - Raw scorecard JSON in an expander
    - Orchestrator reasoning string

Phase 4 layers in: map view, scorecard heatmap, dissent box, why-not summaries,
debate-trace animation, replanning.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from manzil.graph.debate_graph import run_debate  # noqa: E402
from manzil.recommender.pipeline import recommend  # noqa: E402
from manzil.schemas import (  # noqa: E402
    DebateResult,
    GroupType,
    RouteCandidate,
    TravelMode,
    UserQuery,
)

st.set_page_config(page_title="Manzil — Plan", page_icon="🏔️", layout="wide")

st.title("Plan your trip")
st.caption(
    "Fill the form. The recommender returns 3 diverse routes. A team of "
    "specialist agents debates them and picks one — you'll see the scorecard "
    "and the winning day-by-day plan."
)

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
ORIGINS = ["karachi", "lahore", "islamabad"]
STYLE_OPTIONS = [
    "adventure",
    "cultural",
    "photography",
    "relaxation",
    "family",
    "history",
    "trekking",
    "shopping",
]

with st.form("plan_form"):
    cols = st.columns(3)
    with cols[0]:
        group_size = st.number_input("Group size", min_value=1, max_value=20, value=4)
        days = st.number_input("Days", min_value=2, max_value=21, value=7)
        budget_pkr = st.number_input(
            "Budget (PKR)",
            min_value=20_000,
            max_value=2_000_000,
            value=120_000,
            step=10_000,
        )
    with cols[1]:
        group_composition = st.selectbox(
            "Group composition",
            options=[g.value for g in GroupType],
            index=3,
        )
        month_name = st.selectbox("Travel month", options=MONTH_NAMES, index=6)
        travel_mode = st.selectbox(
            "Travel mode preference",
            options=[t.value for t in TravelMode],
            index=0,
        )
    with cols[2]:
        origin_city = st.selectbox("Origin city", options=ORIGINS, index=0)
        difficulty = st.slider(
            "Difficulty tolerance",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = easy / family-friendly · 5 = ambitious / mountainous",
        )
        styles = st.multiselect(
            "Travel styles",
            options=STYLE_OPTIONS,
            default=["cultural", "photography"],
        )

    submitted = st.form_submit_button("Plan my trip", use_container_width=True)


# ---------------------------------------------------------------------------
# Run pipeline on submit
# ---------------------------------------------------------------------------

if submitted:
    query = UserQuery(
        group_size=int(group_size),
        group_composition=GroupType(group_composition),
        budget_pkr=int(budget_pkr),
        days=int(days),
        travel_month=MONTH_NAMES.index(month_name) + 1,
        travel_mode_pref=TravelMode(travel_mode),
        origin_city=origin_city,
        style_tags=list(styles),
        difficulty_tolerance=int(difficulty),
        preferred_destinations=[],
        hard_constraints=[],
    )
    with st.spinner("Recommender → 3 candidate routes…"):
        candidates = recommend(query)
    st.session_state["last_query"] = query
    st.session_state["last_candidates"] = candidates

    with st.spinner("Agents are debating…"):
        result = run_debate(query, candidates)
    st.session_state["last_result"] = result


# ---------------------------------------------------------------------------
# Render persisted results
# ---------------------------------------------------------------------------


def _strip_relaxation_note(rationale: str) -> tuple[str | None, str]:
    """Returns (note_or_none, stripped_rationale)."""
    if not rationale.startswith("⚠"):
        return None, rationale
    parts = rationale.split("\n\n", 1)
    note = parts[0].lstrip("⚠ ").strip()
    rest = parts[1] if len(parts) == 2 else ""
    return note, rest


def _render_candidate_cards(candidates: list[RouteCandidate]):
    if not candidates:
        st.warning(
            "No feasible routes for these constraints — even after relaxation. "
            "Try a different month, a higher difficulty tolerance, or a bigger budget."
        )
        return

    # Relaxation banner — shown once if any candidate has a relaxation note
    notes = []
    for c in candidates:
        note, _ = _strip_relaxation_note(c.rationale)
        if note:
            notes.append(note)
    if notes:
        # All candidates share the same note in this run, so just show the first
        st.info(notes[0])

    st.subheader("Three candidate routes")
    n_cols = max(1, min(3, len(candidates)))
    cols = st.columns(n_cols)
    for i, c in enumerate(candidates):
        with cols[i % n_cols]:
            st.markdown(f"#### {c.label}")
            st.markdown("**Stops:** " + " → ".join(c.destinations))
            st.metric("Estimated cost (PKR)", f"{c.estimated_cost:,}")
            st.caption(f"{c.days} days · ₨{c.estimated_cost // max(1, c.days):,}/day")

            # Diversity axes as small badge-y chips
            chips = " · ".join(
                f"`{k}`: **{v}**" for k, v in c.diversity_axes.items()
            )
            st.markdown(chips)

            # CBR + content scores
            st.caption(
                f"CBR fit {c.cbr_score:.2f} · style fit {c.content_score:.2f}"
            )

            # Strip the relaxation prefix from the rationale we show inline
            _, body = _strip_relaxation_note(c.rationale)
            if body:
                st.write(body)


def _render_winner(result: DebateResult, candidates: list[RouteCandidate]):
    st.divider()
    if result.all_blocked:
        st.error("No safe candidate survived the debate.")
        st.write(result.orchestrator_reasoning)
        st.markdown("**Hard blockers:**")
        for cid, reasons in result.blockers.items():
            st.markdown(f"- `{cid}`")
            for r in reasons:
                st.markdown(f"  - {r}")
        return

    winner = result.winner
    st.subheader(f"Winner — {winner.label}")
    st.write(result.orchestrator_reasoning)

    # --- Scorecard table -----------------------------------------------------
    st.markdown("##### Agent scorecard")
    st.caption("Each agent's score (0–10) for each candidate. Phase 4 turns this into a heatmap.")

    candidate_ids = [c.candidate_id for c in candidates]
    candidate_labels = {c.candidate_id: c.label for c in candidates}

    rows = []
    for agent_name, by_cand in result.scorecard.items():
        row = {"Agent": agent_name}
        for cid in candidate_ids:
            row[candidate_labels[cid]] = round(by_cand.get(cid, 0.0), 1)
        rows.append(row)
    if rows:
        df = pd.DataFrame(rows).set_index("Agent")
        st.dataframe(df, use_container_width=True)

    # --- Blockers (if any) ---------------------------------------------------
    if result.blockers:
        with st.expander("Hard blockers", expanded=False):
            for cid, reasons in result.blockers.items():
                st.markdown(f"**`{cid}`**")
                for r in reasons:
                    st.markdown(f"- {r}")

    # --- Day-by-day plan -----------------------------------------------------
    if result.full_plan and result.full_plan.days:
        st.markdown("##### Day-by-day plan")
        for day in result.full_plan.days:
            stop_names = ", ".join(s.name for s in day.stops) or "(rest day)"
            with st.expander(f"Day {day.day_index} — {stop_names}", expanded=False):
                if day.travel_mode:
                    st.caption(f"Travel mode: {day.travel_mode.value}")
                if day.estimated_cost:
                    st.caption(f"Day budget: PKR {day.estimated_cost:,}")
                if day.weather_note:
                    st.markdown(f"- **Weather:** {day.weather_note}")
                if day.road_note:
                    st.markdown(f"- **Road:** {day.road_note}")
                if day.safety_note:
                    st.markdown(f"- **Safety:** {day.safety_note}")
                for stop in day.stops:
                    if stop.activities:
                        st.markdown(
                            f"- **{stop.name}:** "
                            + ", ".join(stop.activities)
                        )

    # --- Raw debug -----------------------------------------------------------
    with st.expander("Raw scorecard (JSON)", expanded=False):
        st.json(result.model_dump(mode="json"))


if "last_result" in st.session_state and "last_candidates" in st.session_state:
    _render_candidate_cards(st.session_state["last_candidates"])
    _render_winner(st.session_state["last_result"], st.session_state["last_candidates"])
elif not submitted:
    st.info("Submit the form above to see the recommender output and the debate.")
