"""
Debate trace animation.

A streaming animation where each agent's argument fades in as it completes.
Cosmetic, but makes the debate feel real and is great in the demo.

Uses st.empty() + time.sleep(0.4) between steps.
Must guard against Streamlit rerun loops with session_state.
"""

from __future__ import annotations

import time
from typing import List

import streamlit as st

from manzil.schemas import AgentArgument

AGENT_EMOJIS = {
    "WeatherAgent": "🌤️",
    "RoadAgent": "🛣️",
    "SafetyAgent": "🛡️",
    "BudgetAgent": "💰",
    "LocalAgent": "🍲",
}


_AGENT_ORDER = [
    "SafetyAgent",
    "BudgetAgent",
    "WeatherAgent",
    "RoadAgent",
    "LocalAgent",
]


def _group_by_agent(arguments: List[AgentArgument]) -> dict[str, List[AgentArgument]]:
    """Group arguments by agent name."""
    by_agent: dict[str, List[AgentArgument]] = {}
    for arg in arguments:
        by_agent.setdefault(arg.agent_name, []).append(arg)
    return by_agent


def render_debate_trace(arguments: List[AgentArgument]) -> None:
    """
    Render an animated debate trace. Each agent's argument appears
    one by one with a small delay.

    Args:
        arguments: List of agent arguments to animate.
    """
    if not arguments:
        return

    # Use session_state to avoid re-animating on every rerun
    state_key = "debate_trace_done"
    if st.session_state.get(state_key):
        # Already animated this session — show static summary
        _render_static_summary(arguments)
        return

    st.markdown("##### Agents are debating…")
    placeholder = st.empty()

    by_agent = _group_by_agent(arguments)

    shown_lines: List[str] = []
    for agent_name in _AGENT_ORDER:
        agent_args = by_agent.get(agent_name, [])
        if not agent_args:
            continue

        emoji = AGENT_EMOJIS.get(agent_name, "🤖")
        # Show summary line for this agent
        scores = [f"{a.candidate_id}: {a.score:.1f}" for a in agent_args]
        line = f"{emoji} **{agent_name}** — {' | '.join(scores)}"
        shown_lines.append(line)

        # Update placeholder
        placeholder.markdown("<br>".join(shown_lines), unsafe_allow_html=True)
        time.sleep(0.4)

    # Mark as done so we don't re-animate
    st.session_state[state_key] = True

    # Replace with a cleaner static version
    placeholder.empty()
    _render_static_summary(arguments)


def _render_static_summary(arguments: List[AgentArgument]) -> None:
    st.markdown("##### Agent debate complete")
    by_agent = _group_by_agent(arguments)

    for agent_name in _AGENT_ORDER:
        agent_args = by_agent.get(agent_name, [])
        if not agent_args:
            continue
        emoji = AGENT_EMOJIS.get(agent_name, "🤖")
        scores = [f"{a.candidate_id}: {a.score:.1f}" for a in agent_args]
        st.markdown(f"{emoji} **{agent_name}** — {' | '.join(scores)}")
