"""
Agent math / orchestrator internal trace component.

Shows the step-by-step math the Orchestrator used to pick a winner:
1. Hard-blocker elimination
2. Weighted aggregate per candidate (with formula table)
3. Epsilon tie-break (if triggered)
4. Dissent detection
5. Why-not generation

Uses session_state to avoid re-animating on reruns.
"""

from __future__ import annotations

import time
from typing import List

import streamlit as st

from manzil.schemas import DebateTrace, OrchestratorTrace

STEP_TITLES = [
    "Agent Evaluation — Scores Received",
    "Step 1 — Hard-Blocker Elimination",
    "Step 2 — Weighted Aggregate Score",
    "Step 3 — Epsilon Tie-Break",
    "Step 4 — Dissent Detection",
    "Step 5 — Why the Runner-Ups Lost",
]


def render_agent_math(trace: DebateTrace | None) -> None:
    """
    Render the orchestrator's internal math as an animated step-by-step reveal.
    """
    if not trace or not trace.orchestrator:
        return

    orch = trace.orchestrator
    state_key = "agent_math_done"
    if st.session_state.get(state_key):
        _render_static_agent_math(orch)
        return

    st.markdown("#### How the winner was chosen")
    st.caption("A step-by-step breakdown of the multi-agent debate math.")

    placeholder = st.empty()
    shown_steps: List[str] = []

    # Step 0: Raw scores
    _step_raw_scores(shown_steps, trace, placeholder)
    time.sleep(0.3)

    # Step 1: Blockers
    _step_blockers(shown_steps, orch, placeholder)
    time.sleep(0.3)

    # Step 2: Weighted aggregate
    _step_aggregate(shown_steps, orch, placeholder)
    time.sleep(0.3)

    # Step 3: Tie-break
    _step_tie_break(shown_steps, orch, placeholder)
    time.sleep(0.3)

    # Step 4: Dissent
    _step_dissent(shown_steps, orch, placeholder)
    time.sleep(0.3)

    # Step 5: Why not
    _step_why_not(shown_steps, orch, placeholder)

    st.session_state[state_key] = True
    placeholder.empty()
    _render_static_agent_math(orch)


def _step_raw_scores(shown_steps: List[str], trace: DebateTrace, placeholder) -> None:
    lines = [
        f"**{STEP_TITLES[0]}**",
        "Each of the 5 specialist agents evaluated all 3 candidates.",
        "",
    ]
    # Group by agent
    by_agent: dict = {}
    for arg in trace.arguments:
        by_agent.setdefault(arg.agent_name, []).append(arg)

    for agent_name, args in by_agent.items():
        scores = [f"`{a.candidate_id}`: {a.score:.1f}" for a in args]
        blocker = any(a.hard_blocker for a in args)
        emoji = "🚫" if blocker else ""
        lines.append(f"- **{agent_name}** {emoji} — {' | '.join(scores)}")

    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_blockers(shown_steps: List[str], orch: OrchestratorTrace, placeholder) -> None:
    lines = [
        f"**{STEP_TITLES[1]}**",
        "Candidates with hard blockers from any agent are disqualified.",
        "",
        f"- Surviving: {', '.join(orch.surviving_ids) if orch.surviving_ids else 'None'}",
        f"- Blocked: {', '.join(orch.blocked_ids) if orch.blocked_ids else 'None'}",
    ]
    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_aggregate(shown_steps: List[str], orch: OrchestratorTrace, placeholder) -> None:
    lines = [
        f"**{STEP_TITLES[2]}**",
        "Aggregate = Σ(agent_score × weight × confidence) / Σ(weight × confidence)",
        "",
    ]
    for ca in orch.candidates:
        lines.append(f"**{ca.candidate_label}** (`{ca.candidate_id}`)")
        if ca.agent_details:
            lines.append(
                "| Agent | Weight | Raw Score | Confidence | Eff. Weight | Contribution |"
            )
            lines.append("|---|---|---|---|---|---|")
            for d in ca.agent_details:
                lines.append(
                    f"| {d.agent_name} | {d.weight} | {d.raw_score} | {d.confidence} "
                    f"| {d.effective_weight} | {d.contribution} |"
                )
        lines.append(
            f"- Total weighted: **{ca.total_weighted}** / Effective weight: **{ca.total_effective_weight}**"
        )
        lines.append(f"- **Aggregate score: {ca.aggregate_score}**")
        lines.append(f"- Concentration (max−min): **{ca.concentration}**")
        lines.append("")
    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_tie_break(shown_steps: List[str], orch: OrchestratorTrace, placeholder) -> None:
    tb = orch.tie_break
    if not tb:
        lines = [
            f"**{STEP_TITLES[3]}**",
            "No tie-break data available.",
        ]
    else:
        lines = [
            f"**{STEP_TITLES[3]}**",
            f"Epsilon = **{tb.epsilon}**. If top-2 gap ≤ epsilon, lower concentration wins.",
            "",
            f"- Top: `{tb.top_candidate_id}` = {tb.top_score}",
            f"- Second: `{tb.second_candidate_id}` = {tb.second_score}",
            f"- Gap: **{tb.gap}**",
            f"- Triggered: **{'Yes' if tb.triggered else 'No'}**",
        ]
        if tb.triggered:
            lines.extend([
                f"- Top concentration: {tb.top_concentration}",
                f"- Second concentration: {tb.second_concentration}",
                f"- **Winner: `{tb.winner_id}`**",
            ])
        lines.append(f"- {tb.reason}")
    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_dissent(shown_steps: List[str], orch: OrchestratorTrace, placeholder) -> None:
    d = orch.dissent
    lines = [f"**{STEP_TITLES[4]}**", f"Threshold = **{d.threshold}** points.", ""]
    if d.had_dissent and d.dissent_lines:
        for line in d.dissent_lines:
            lines.append(f"- 🗣️ {line}")
    else:
        lines.append("- ✅ No dissent — all agents agreed within threshold.")
    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_why_not(shown_steps: List[str], orch: OrchestratorTrace, placeholder) -> None:
    lines = [f"**{STEP_TITLES[5]}**", ""]
    if orch.why_not:
        for wn in orch.why_not:
            lines.append(
                f"- **{wn.runner_up_label}** (`{wn.runner_up_id}`): "
                f"agg {wn.aggregate_score} vs winner {wn.winner_score} "
                f"(Δ {wn.delta})"
            )
            if wn.worst_agent:
                lines.append(f"  - Weakest agent: {wn.worst_agent} ({wn.worst_agent_score})")
            lines.append(f"  - {wn.explanation}")
    else:
        lines.append("- No runner-up data.")
    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _render_static_agent_math(orch: OrchestratorTrace) -> None:
    st.markdown("#### How the winner was chosen")
    st.caption("A step-by-step breakdown of the multi-agent debate math.")

    with st.expander(STEP_TITLES[0], expanded=False):
        st.caption("Raw scores from each agent for each candidate.")
        # Already shown in scorecard, keep this light
        st.markdown("See the **Agent Scorecard** heatmap above for raw scores.")

    with st.expander(STEP_TITLES[1], expanded=False):
        st.markdown(f"- Surviving: **{', '.join(orch.surviving_ids) if orch.surviving_ids else 'None'}**")
        st.markdown(f"- Blocked: **{', '.join(orch.blocked_ids) if orch.blocked_ids else 'None'}**")

    with st.expander(STEP_TITLES[2], expanded=False):
        st.markdown("**Formula:** `Σ(score × weight × confidence) / Σ(weight × confidence)`")
        for ca in orch.candidates:
            st.markdown(f"**{ca.candidate_label}** (`{ca.candidate_id}`)")
            if ca.agent_details:
                df = [
                    {
                        "Agent": d.agent_name,
                        "Weight": d.weight,
                        "Raw": d.raw_score,
                        "Conf": d.confidence,
                        "Eff.Weight": d.effective_weight,
                        "Contribution": d.contribution,
                    }
                    for d in ca.agent_details
                ]
                st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown(f"**Aggregate: {ca.aggregate_score}** · Concentration: {ca.concentration}")
            st.divider()

    with st.expander(STEP_TITLES[3], expanded=False):
        tb = orch.tie_break
        if tb:
            st.markdown(f"Epsilon = **{tb.epsilon}**")
            st.markdown(f"Top: `{tb.top_candidate_id}` = {tb.top_score}")
            st.markdown(f"Second: `{tb.second_candidate_id}` = {tb.second_score}")
            st.markdown(f"Gap: **{tb.gap}** · Triggered: **{'Yes' if tb.triggered else 'No'}**")
            if tb.triggered:
                st.markdown(f"Top concentration: {tb.top_concentration}")
                st.markdown(f"Second concentration: {tb.second_concentration}")
            st.markdown(f"**Winner: `{tb.winner_id}`**")
            st.info(tb.reason)
        else:
            st.caption("No tie-break data.")

    with st.expander(STEP_TITLES[4], expanded=False):
        d = orch.dissent
        st.markdown(f"Dissent threshold: **{d.threshold}** points")
        if d.had_dissent:
            for line in d.dissent_lines:
                st.warning(line)
        else:
            st.success("No dissent — all agents agreed within threshold.")

    with st.expander(STEP_TITLES[5], expanded=False):
        if orch.why_not:
            for wn in orch.why_not:
                st.markdown(f"**{wn.runner_up_label}** (`{wn.runner_up_id}`)")
                st.markdown(f"- Aggregate: {wn.aggregate_score} vs winner {wn.winner_score} (Δ {wn.delta})")
                if wn.worst_agent:
                    st.markdown(f"- Weakest agent: {wn.worst_agent} ({wn.worst_agent_score})")
                st.caption(wn.explanation)
        else:
            st.caption("No runner-up data.")


__all__ = ["render_agent_math"]
