"""
Live debate visualization component.

Renders agent status cards that fill in live as the LangGraph stream yields
intermediate results. Designed for Full LLM Mode where each agent makes
an independent LLM call.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import streamlit as st

from manzil.schemas import AgentArgument, DebateResult, RouteCandidate

_AGENT_LABELS: Dict[str, str] = {
    "weather": "WeatherAgent",
    "road": "RoadAgent",
    "safety": "SafetyAgent",
    "budget": "BudgetAgent",
    "local": "LocalAgent",
}


def render_debate_live(
    stream_events,
    candidates: List[RouteCandidate],
) -> Optional[DebateResult]:
    """
    Consume the stream generator and render live agent cards.

    Each agent card appears at the bottom of the UI as the stream yields it,
    with expandable reasons and concerns. Returns the final ``DebateResult``.

    Args:
        stream_events: Generator yielding ``{"type": "agent_done"|"orchestrator_done", ...}``.
        candidates: The candidate routes.
    """
    status: Dict[str, dict] = {
        key: {"status": "pending", "arguments": None} for key in _AGENT_LABELS
    }
    completed = 0
    result: Optional[DebateResult] = None

    candidate_labels = {c.candidate_id: c.label for c in (candidates or [])}

    st.markdown("#### Agent Debate")

    progress_bar = st.progress(0, text="0 / 5 agents done")

    for event in stream_events:
        if event["type"] == "agent_done":
            agent = event["agent"]
            status[agent] = {"status": "done", "arguments": event["arguments"]}
            completed += 1
            progress_bar.progress(
                completed / 5,
                text=f"{completed} / 5 agents done",
            )
            _render_card(agent, status[agent], candidate_labels)
            time.sleep(0.3)

        elif event["type"] == "orchestrator_done":
            result = event["result"]

    progress_bar.empty()

    if result and result.all_blocked:
        st.error("All candidates were blocked — no winner")
    elif result and result.winner:
        st.success(f"Winner: {result.winner.label}")
    else:
        st.info("Debate complete — no winner selected")

    return result


def _render_card(
    agent_key: str,
    info: dict,
    candidate_labels: Dict[str, str],
) -> None:
    """Append a single agent status card at the current cursor position."""
    label = _AGENT_LABELS.get(agent_key, agent_key)

    if info["status"] == "done" and info["arguments"]:
        args: List[AgentArgument] = info["arguments"]
        avg_score = sum(a.score for a in args) / len(args)
        st.markdown(f"**{label}**  ✅ — Avg: **{avg_score:.1f}/10**")

        detail_parts = []
        for a in args:
            c_label = candidate_labels.get(a.candidate_id, a.candidate_id)
            part = f"**{c_label}**: {a.score:.1f}/10"
            if a.hard_blocker:
                part += " 🚫"
            detail_parts.append(part)
        st.caption(" | ".join(detail_parts))

        with st.expander(f"See {label} arguments"):
            for a in args:
                c_label = candidate_labels.get(
                    a.candidate_id, a.candidate_id
                )
                st.markdown(f"**{c_label}** — {a.score:.1f}/10")
                if a.hard_blocker:
                    st.error(f"🚫 {a.hard_blocker}")
                if a.supporting_reasons:
                    for r in a.supporting_reasons[:3]:
                        st.markdown(f"- 👍 {r}")
                if a.concerns:
                    for c in a.concerns[:3]:
                        st.markdown(f"- ⚠ {c}")
    else:
        st.markdown(f"**{label}**  ⏳ *Pending*")


__all__ = ["render_debate_live"]
