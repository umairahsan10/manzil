"""
Why-not summaries renderer.

Renders one-line plain-language explanations for each runner-up:
what it offered, why it lost, and under what conditions it might have won.
"""

from __future__ import annotations

from typing import Dict

import streamlit as st


def render_why_not(why_not: Dict[str, str], candidate_labels: Dict[str, str]) -> None:
    """
    Render why-not summaries for runner-up candidates.

    Args:
        why_not: why_not[candidate_id] = one-line explanation.
        candidate_labels: Mapping from candidate_id to human-readable label.
    """
    if not why_not:
        return

    st.markdown("##### Why the runner-ups lost")
    for cid, reason in why_not.items():
        label = candidate_labels.get(cid, cid)
        st.markdown(f"- **{label}:** {reason}")

    st.caption(
        "These summaries explain what each alternative offered and why it was "
        "passed over. If your priorities differ, one of these might still suit you."
    )
