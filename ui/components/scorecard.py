"""
Scorecard heatmap component.

The hero widget: a 5×3 heatmap (agents × candidates) with cell coloring
by score. Veto cells are crossed out and tinted red. Clicking a cell
reveals that agent's reasons and concerns for that candidate.
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from manzil.schemas import AgentArgument, RouteCandidate


def render_scorecard(
    candidates: List[RouteCandidate],
    arguments: List[AgentArgument],
    scorecard: Dict[str, Dict[str, float]],
    blockers: Dict[str, List[str]],
) -> None:
    """
    Render the interactive agent scorecard heatmap.

    Args:
        candidates: The candidate routes.
        arguments: Full agent arguments (used for detail panel).
        scorecard: scorecard[agent_name][candidate_id] = score.
        blockers: blockers[candidate_id] = list of blocker reasons.
    """
    if not scorecard:
        st.caption("No scorecard data available.")
        return

    agent_names = list(scorecard.keys())
    candidate_ids = [c.candidate_id for c in candidates]
    candidate_labels = {c.candidate_id: c.label for c in candidates}

    # --- Heatmap table ---
    st.markdown("##### Agent Scorecard")
    st.caption("Scores are out of 10. Red strikethrough = hard blocker (veto). Click a row to see details.")

    # Build HTML table
    html = "<table style='width:100%; border-collapse:collapse; text-align:center;'>"

    # Header row
    html += "<tr style='background:#f8f9fa;'>"
    html += "<th style='padding:8px; border:1px solid #ddd; text-align:left;'>Agent</th>"
    for cid in candidate_ids:
        label = candidate_labels.get(cid, cid)
        html += f"<th style='padding:8px; border:1px solid #ddd;'>{label}</th>"
    html += "</tr>"

    # Data rows
    for agent_name in agent_names:
        html += "<tr>"
        html += f"<td style='padding:8px; border:1px solid #ddd; text-align:left; font-weight:600;'>{agent_name}</td>"
        for cid in candidate_ids:
            score = scorecard.get(agent_name, {}).get(cid, 0.0)
            is_blocked = cid in blockers and any(agent_name in b for b in blockers[cid])

            # Color scale: low=red, mid=yellow, high=green
            color = _score_color(score)
            text_color = "white" if score < 3 or score > 7 else "#333"

            if is_blocked:
                cell_style = (
                    f"background:#ffcccc; color:#900; text-decoration:line-through; "
                    f"font-weight:bold; padding:8px; border:1px solid #ddd;"
                )
                display = f"{score:.1f} ✗"
            else:
                cell_style = (
                    f"background:{color}; color:{text_color}; font-weight:600; "
                    f"padding:8px; border:1px solid #ddd;"
                )
                display = f"{score:.1f}"

            html += f"<td style='{cell_style}'>{display}</td>"
        html += "</tr>"

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    # --- Detail panel (selectbox driven) ---
    st.markdown("---")
    detail_cols = st.columns(2)
    with detail_cols[0]:
        selected_agent = st.selectbox("Select agent", agent_names, key="scorecard_agent")
    with detail_cols[1]:
        selected_cand = st.selectbox(
            "Select candidate",
            candidate_ids,
            format_func=lambda cid: candidate_labels.get(cid, cid),
            key="scorecard_cand",
        )

    # Find the argument for this pair
    arg = next(
        (
            a
            for a in arguments
            if a.agent_name == selected_agent and a.candidate_id == selected_cand
        ),
        None,
    )

    if arg:
        st.markdown(f"**{selected_agent} → {candidate_labels.get(selected_cand, selected_cand)}**")
        st.metric("Score", f"{arg.score:.1f}/10", delta="Veto" if arg.hard_blocker else None)
        if arg.supporting_reasons:
            st.markdown("**Supporting reasons:**")
            for r in arg.supporting_reasons:
                st.markdown(f"- {r}")
        if arg.concerns:
            st.markdown("**Concerns:**")
            for r in arg.concerns:
                st.markdown(f"- {r}")
        if arg.hard_blocker:
            st.error(f"**Hard blocker:** {arg.hard_blocker}")
        if arg.confidence < 1.0:
            st.caption(f"Confidence: {arg.confidence:.0%}")
    else:
        st.info("No argument data for this agent-candidate pair.")


def _score_color(score: float) -> str:
    """Return a hex color for a 0-10 score."""
    if score >= 8:
        return "#27ae60"  # green
    if score >= 6:
        return "#f1c40f"  # yellow
    if score >= 4:
        return "#e67e22"  # orange
    return "#c0392b"  # red
