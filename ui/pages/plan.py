"""
Plan page (Streamlit auto-discovered).

The form builds a UserQuery. The recommender returns 3 diverse candidates.
The LangGraph debate runs through 5 real specialist agents in parallel
and the Orchestrator picks a winner.

Phase 4 layers in:
    - Map view with candidate routes
    - Scorecard heatmap (hero widget)
    - Debate-trace animation
    - Dissent + why-not blocks
    - Side-by-side replanning UI
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

from manzil.agents.base import is_full_llm_mode, set_full_llm_mode  # noqa: E402
from manzil.graph.debate_graph import run_debate, run_debate_stream  # noqa: E402
from manzil.recommender.pipeline import recommend_with_trace  # noqa: E402
from manzil.replan import replan  # noqa: E402
from manzil.schemas import (  # noqa: E402
    DebateResult,
    Disruption,
    GroupType,
    RecommendationTrace,
    RouteCandidate,
    TravelMode,
    UserQuery,
)
from ui.components.map_view import render_map  # noqa: E402
from ui.components.scorecard import render_scorecard  # noqa: E402
from ui.components.day_by_day import render_day_by_day  # noqa: E402
from ui.components.dissent import render_dissent  # noqa: E402
from ui.components.why_not import render_why_not  # noqa: E402
from ui.components.debate_live import render_debate_live  # noqa: E402
from ui.components.rs_trace import render_rs_trace  # noqa: E402
from ui.components.agent_math import render_agent_math  # noqa: E402
st.set_page_config(page_title="Manzil — Plan", page_icon="🏔️", layout="wide")

st.title("Plan your trip")
st.caption(
    "Fill the form. The recommender returns 3 diverse routes. A team of "
    "specialist agents debates them and picks one — you'll see the scorecard, "
    "map, and the winning day-by-day plan."
)

# ---------------------------------------------------------------------------
# Helpers (defined before use)
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

    notes = []
    for c in candidates:
        note, _ = _strip_relaxation_note(c.rationale)
        if note:
            notes.append(note)
    if notes:
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

            chips = " · ".join(
                f"`{k}`: **{v}**" for k, v in c.diversity_axes.items()
            )
            st.markdown(chips)

            st.caption(
                f"CBR fit {c.cbr_score:.2f} · style fit {c.content_score:.2f}"
            )

            _, body = _strip_relaxation_note(c.rationale)
            if body:
                st.write(body)


def _render_winner(result: DebateResult | None, candidates: list[RouteCandidate]):
    if result is None:
        return

    st.divider()

    # --- RS Trace: how routes were selected ---
    rs_trace = st.session_state.get("last_rs_trace")
    if rs_trace:
        render_rs_trace(rs_trace)

    st.divider()

    # --- Scorecard (render even when all blocked — shows why each failed) ---
    if result.scorecard:
        render_scorecard(
            candidates=candidates,
            arguments=result.arguments,
            scorecard=result.scorecard,
            blockers=result.blockers,
        )

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
    if not winner:
        st.warning("No winner was selected.")
        return

    st.subheader(f"Winner — {winner.label}")
    st.write(result.orchestrator_reasoning)

    if result.blockers:
        with st.expander("Hard blockers", expanded=False):
            for cid, reasons in result.blockers.items():
                st.markdown(f"**`{cid}`**")
                for r in reasons:
                    st.markdown(f"- {r}")

    if result.full_plan and result.full_plan.days:
        render_day_by_day(result.full_plan)

    render_dissent(result.dissenting_opinion)

    candidate_labels = {c.candidate_id: c.label for c in candidates}
    render_why_not(result.why_not, candidate_labels)

    # --- Agent math trace: how winner was chosen ---
    if result.debate_trace:
        st.divider()
        render_agent_math(result.debate_trace)

    with st.expander("Raw result (JSON)", expanded=False):
        st.json(result.model_dump(mode="json"))


def _render_replan_ui():
    st.divider()
    with st.expander("🔄 Replan with disruption…", expanded=False):
        st.caption(
            "Simulate a mid-trip disruption and see how the recommendation changes."
        )

        dis_kind = st.selectbox(
            "Disruption type",
            options=["road_closed", "budget_cut", "weather_event", "flight_cancelled"],
            format_func=lambda k: {
                "road_closed": "Road closed (pass blocked)",
                "budget_cut": "Budget cut",
                "weather_event": "Weather event",
                "flight_cancelled": "Flight cancelled",
            }.get(k, k),
            key="replan_kind",
        )

        dis_params = {}
        if dis_kind == "road_closed":
            dis_params["pass_id"] = st.text_input("Pass ID", value="babusar", help="e.g. babusar, lowari", key="replan_pass")
            dis_params["day_index"] = st.number_input("Day affected", min_value=1, max_value=21, value=3, key="replan_day")
        elif dis_kind == "budget_cut":
            dis_params["pct_cut"] = st.number_input("Budget cut (%)", min_value=5, max_value=90, value=20, key="replan_pct")
        elif dis_kind == "weather_event":
            dis_params["destination_id"] = st.text_input("Destination affected", value="naran", key="replan_dest")
            dis_params["day_index"] = st.number_input("Day affected", min_value=1, max_value=21, value=3, key="replan_wday")
        elif dis_kind == "flight_cancelled":
            dis_params["destination_id"] = st.text_input("Flight destination", value="skardu", key="replan_fdest")

        description = st.text_input("Description", value=f"{dis_kind} disruption", key="replan_desc")

        if st.button("Replan", use_container_width=True, key="replan_btn"):
            original_query = st.session_state.get("last_query")
            if not original_query:
                st.error("No original query found in session state.")
            else:
                disruption = Disruption(
                    kind=dis_kind,
                    description=description,
                    **{k: v for k, v in dis_params.items() if v is not None},
                )
                with st.spinner("Replanning…"):
                    new_result = replan(original_query, disruption)
                st.session_state["replan_result"] = new_result
                st.rerun()

    replan_result = st.session_state.get("replan_result")
    if replan_result:
        st.markdown("---")
        st.subheader("Side-by-side: Original vs. Replan")

        col_orig, col_replan = st.columns(2)

        original_result = st.session_state.get("last_result")
        with col_orig:
            st.markdown("**Original winner**")
            if original_result and original_result.winner:
                st.markdown(f"### {original_result.winner.label}")
                st.caption(original_result.orchestrator_reasoning)
                if original_result.full_plan:
                    render_day_by_day(original_result.full_plan, title="Plan")
            else:
                st.caption("No original winner.")

        with col_replan:
            st.markdown("**Replan winner**")
            if replan_result.all_blocked:
                st.error("All candidates blocked after disruption.")
                st.write(replan_result.orchestrator_reasoning)
            elif replan_result.winner:
                st.markdown(f"### {replan_result.winner.label}")
                st.caption(replan_result.orchestrator_reasoning)
                if replan_result.full_plan:
                    render_day_by_day(replan_result.full_plan, title="Plan")
            else:
                st.caption("No winner.")

        if original_result and original_result.winner and replan_result and replan_result.winner:
            orig_id = original_result.winner.candidate_id
            replan_id = replan_result.winner.candidate_id
            if orig_id != replan_id:
                st.success(f"Winner changed from **{orig_id}** to **{replan_id}**.")
            else:
                st.info("Winner stayed the same, but details may have shifted.")


# ---------------------------------------------------------------------------
# Mode toggle
# ---------------------------------------------------------------------------

mode_col1, mode_col2 = st.columns([3, 1])
with mode_col1:
    pass
with mode_col2:
    use_full_llm = st.toggle(
        "Full LLM Mode",
        value=is_full_llm_mode(),
        help=(
            "ON: Each agent generates unique prose (16 API calls/debate, premium quality). "
            "OFF: Templated arguments (1 API call/debate, fast & free-tier friendly)."
        ),
    )
    if use_full_llm != is_full_llm_mode():
        set_full_llm_mode(use_full_llm)
        st.rerun()

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
        is_foreign = st.checkbox(
            "I am a foreign national (requires NOC for restricted zones)",
            value=False,
        )
        elderly = st.checkbox(
            "Group includes someone over 60 years old",
            value=False,
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
        is_foreign_traveller=bool(is_foreign),
        elderly_in_group=bool(elderly),
    )
    st.session_state["last_query"] = query
    st.session_state.pop("last_candidates", None)
    st.session_state.pop("last_result", None)
    st.session_state.pop("replan_result", None)
    st.session_state.pop("last_rs_trace", None)
    st.session_state.pop("rs_trace_done", None)
    st.session_state.pop("agent_math_done", None)

    with st.spinner("Recommender → 3 candidate routes…"):
        candidates, rs_trace = recommend_with_trace(query)
    st.session_state["last_candidates"] = candidates
    st.session_state["last_rs_trace"] = rs_trace

    if candidates:
        if use_full_llm:
            events = run_debate_stream(query, candidates, use_full_llm=True)
            result = render_debate_live(events, candidates)
        else:
            with st.spinner("Agents are debating…"):
                result = run_debate(query, candidates, use_full_llm=False)
        st.session_state["last_result"] = result
    else:
        st.session_state["last_result"] = None


# ---------------------------------------------------------------------------
# Render persisted results
# ---------------------------------------------------------------------------

if "last_result" in st.session_state:
    candidates = st.session_state.get("last_candidates", [])
    result = st.session_state["last_result"]

    if candidates:
        _render_candidate_cards(candidates)

        st.markdown("---")
        winner_id = result.winner.candidate_id if result and result.winner else None
        render_map(
            candidates,
            winner_id=winner_id,
            day_plan=result.full_plan if result else None,
        )

    _render_winner(result, candidates)

    if result and not result.all_blocked:
        _render_replan_ui()

elif not submitted:
    st.info("Submit the form above to see the recommender output and the debate.")
