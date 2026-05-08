"""
Day-by-day plan renderer.

Renders the DayByDayPlan for the winning route. Per day: stop list,
drive segment, weather note, road note, safety flag, one local-experience tip.
Collapsible per day.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from manzil.schemas import DayByDayPlan, DayPlan


def render_day_by_day(plan: DayByDayPlan, title: str = "Day-by-day plan") -> None:
    """
    Render a day-by-day plan with collapsible days.

    Args:
        plan: The DayByDayPlan to render.
        title: Section title.
    """
    if not plan or not plan.days:
        st.caption("No day-by-day plan available.")
        return

    st.markdown(f"##### {title}")
    st.caption(f"Total estimated cost: PKR {plan.total_cost:,}")

    for day in plan.days:
        _render_day(day)


def _render_day(day: DayPlan) -> None:
    stop_names = ", ".join(s.name for s in day.stops) or "(travel day)"
    with st.expander(f"Day {day.day_index} — {stop_names}", expanded=False):
        cols = st.columns([2, 1])
        with cols[0]:
            if day.travel_mode:
                st.caption(f"Travel mode: {day.travel_mode.value}")
            if day.drive_time_hours is not None:
                st.caption(f"Drive time: {day.drive_time_hours:.1f} hours")
            if day.estimated_cost:
                st.caption(f"Day budget: PKR {day.estimated_cost:,}")

        with cols[1]:
            # Safety flag gets prominence
            if day.safety_note:
                st.warning(day.safety_note)

        # Notes
        if day.weather_note:
            st.markdown(f"**Weather:** {day.weather_note}")
        if day.road_note:
            st.markdown(f"**Road:** {day.road_note}")

        # Stops with activities and local tips
        for stop in day.stops:
            st.markdown(f"**📍 {stop.name}**")
            if stop.activities:
                st.caption(
                    "Activities: " + ", ".join(stop.activities),
                )
            if stop.local_tip:
                st.info(f"💡 Local tip: {stop.local_tip}")

        st.divider()
