"""
Dissent opinion renderer.

Pulls DebateResult.dissenting_opinion and renders it inside an
alert-style box only when non-null.
"""

from __future__ import annotations

import streamlit as st


def render_dissent(dissenting_opinion: str | None) -> None:
    """
    Render the dissenting opinion if one exists.

    Args:
        dissenting_opinion: The natural-language dissent string, or None.
    """
    if not dissenting_opinion:
        return

    st.markdown("##### Dissenting opinion")
    st.info(
        f"🗣️ {dissenting_opinion}\n\n"
        "*One agent strongly disagreed with this pick. Consider their view if "
        "their domain matters most to you.*"
    )
