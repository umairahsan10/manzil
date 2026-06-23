"""
Map view component.

Shows candidate routes as colored polylines on a Folium map.
Once a winner is picked, the winning route is bolded and runner-ups faded.
Stops are circle markers with hover popups (name, altitude, day index).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import folium
import streamlit as st
from streamlit_folium import st_folium

from manzil.data_loader import load_destinations
from manzil.schemas import DayByDayPlan, RouteCandidate

# Route colors for the 3 candidates
ROUTE_COLORS = ["#e74c3c", "#3498db", "#2ecc71"]  # red, blue, green
WINNER_COLOR = "#f39c12"  # orange for winner when highlighted
FADED_OPACITY = 0.25


def render_map(
    candidates: List[RouteCandidate],
    winner_id: Optional[str] = None,
    day_plan: Optional[DayByDayPlan] = None,
    height: int = 450,
) -> None:
    """
    Render a Folium map with candidate routes.

    Args:
        candidates: Up to 3 candidate routes.
        winner_id: If set, highlight this route and fade others.
        day_plan: Optional day-by-day plan to annotate stops with day indices.
        height: Map height in pixels.
    """
    destinations_by_id = load_destinations()

    # Compute center from all candidate stops
    all_coords = []
    for c in candidates:
        for dest_id in c.destinations:
            dest = destinations_by_id.get(dest_id)
            if dest:
                all_coords.append(dest.coords)

    if not all_coords:
        # Fallback: center on northern Pakistan
        center = [35.5, 74.5]
        zoom = 6
    else:
        lats = [c[0] for c in all_coords]
        lons = [c[1] for c in all_coords]
        center = [sum(lats) / len(lats), sum(lons) / len(lons)]
        zoom = 7

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

    # Build day index lookup from day_plan if provided
    day_index_for_stop: Dict[str, int] = {}
    if day_plan:
        for day in day_plan.days:
            for stop in day.stops:
                # Use first occurrence
                if stop.destination_id not in day_index_for_stop:
                    day_index_for_stop[stop.destination_id] = day.day_index

    for i, candidate in enumerate(candidates):
        is_winner = winner_id and candidate.candidate_id == winner_id

        color = WINNER_COLOR if is_winner else ROUTE_COLORS[i % len(ROUTE_COLORS)]
        opacity = 1.0 if not winner_id else (1.0 if is_winner else FADED_OPACITY)
        weight = 5 if is_winner else (3 if not winner_id else 2)

        # Resolve destinations once, reuse for polyline + markers
        route_dests = [
            destinations_by_id[dest_id]
            for dest_id in candidate.destinations
            if dest_id in destinations_by_id
        ]
        route_coords = [dest.coords for dest in route_dests]

        # Draw polyline
        if len(route_coords) >= 2:
            folium.PolyLine(
                locations=route_coords,
                color=color,
                weight=weight,
                opacity=opacity,
                tooltip=f"{candidate.label} (₨{candidate.estimated_cost:,})",
            ).add_to(m)

        # Draw stop markers
        for dest in route_dests:
            day_idx = day_index_for_stop.get(dest.id)
            day_str = f" · Day {day_idx}" if day_idx else ""

            popup_html = (
                f"<b>{dest.name}</b><br>"
                f"Altitude: {dest.altitude_m} m<br>"
                f"Region: {dest.region}{day_str}"
            )

            radius = 7 if is_winner else 5
            folium.CircleMarker(
                location=dest.coords,
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=opacity,
                popup=folium.Popup(popup_html, max_width=200),
            ).add_to(m)

    # Add a small legend
    legend_html = """
    <div style="
        position: fixed;
        bottom: 10px; left: 10px;
        background: white;
        padding: 8px 12px;
        border-radius: 4px;
        box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        font-size: 12px;
        z-index: 9999;
    ">
        <b>Routes</b><br>
    """
    for i, c in enumerate(candidates):
        col = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        legend_html += f'<span style="color:{col}">&#9679;</span> {c.label}<br>'
    if winner_id:
        legend_html += f'<span style="color:{WINNER_COLOR}">&#9679;</span> Winner<br>'
    legend_html += "</div>"

    m.get_root().html.add_child(folium.Element(legend_html))

    with st.container():
        st_folium(m, width="100%", height=height, returned_objects=[])
