"""
Cost calculator — deterministic cost decomposition.

Pure Python over `data/costs.json`. No LLM. No API calls.

Decomposes a route into:
    - transport (per segment, per mode, per group size)
    - lodging (per night, per quality tier inferred from budget)
    - food (per person per day)
    - activities (per day)
    - buffer (10%)

Returns a `CostBreakdown` schema instance.
"""

from __future__ import annotations

from typing import Dict, Optional

from manzil.data_loader import load_costs
from manzil.schemas import CostBreakdown, RouteCandidate, UserQuery


def _season_for_month(month: int) -> str:
    costs = load_costs()
    seasons = costs.get("_meta", {}).get("season_definition", {})
    for season_name, months in seasons.items():
        if month in months:
            return season_name
    return "low"


def _region_for_destination(dest_id: str) -> str:
    """Map destination id to cost region."""
    gb = {
        "hunza-karimabad", "skardu", "fairy-meadows", "gilgit",
        "passu", "attabad", "khaplu", "deosai",
    }
    kpk = {"naran", "swat-kalam", "shogran", "chitral"}
    ajk = {"neelum"}
    punjab = {"murree"}
    if dest_id in gb:
        return "gilgit-baltistan"
    if dest_id in kpk:
        return "khyber-pakhtunkhwa"
    if dest_id in ajk:
        return "azad-kashmir"
    if dest_id in punjab:
        return "punjab"
    return "gilgit-baltistan"  # default


def _quality_tier(budget_per_day: float) -> str:
    """Infer lodging quality tier from per-day budget."""
    if budget_per_day <= 2500:
        return "low"
    if budget_per_day <= 7000:
        return "mid"
    return "high"


def estimate_cost(
    route: RouteCandidate,
    query: UserQuery,
    quality_tier: Optional[str] = None,
) -> CostBreakdown:
    """
    Decompose the total cost of a route for a given query.

    Transport is looked up from costs.json (origin->first-dest and
    inter-destination segments). Lodging is per-night × group size.
    Food and activities are per-person-per-day × group size × nights.
    """
    costs = load_costs()
    season = _season_for_month(query.travel_month)

    # Determine quality tier from budget if not provided
    if quality_tier is None:
        per_day = query.budget_pkr / max(1, query.days)
        quality_tier = _quality_tier(per_day)

    # --- Transport ---------------------------------------------------------
    transport_total = 0
    origin = query.origin_city.lower()
    first_dest = route.destinations[0] if route.destinations else ""

    # Origin -> first destination
    transport_db = costs.get("transport", {})
    origin_map = transport_db.get(origin, {})
    first_leg = origin_map.get(first_dest, {})
    mode_str = route.travel_modes[0].value if route.travel_modes else "road"
    transport_total += int(first_leg.get(mode_str, first_leg.get("road", 0)))

    # Inter-destination hops
    inter_db = costs.get("inter_destination", {})
    for i in range(1, len(route.destinations)):
        prev = route.destinations[i - 1]
        dest = route.destinations[i]
        mode_str = (
            route.travel_modes[i].value
            if i < len(route.travel_modes)
            else "road"
        )
        key = f"{prev}__{dest}"
        seg = inter_db.get(key, {})
        transport_total += int(seg.get(mode_str, seg.get("road", 0)))

    # --- Lodging -----------------------------------------------------------
    lodging_total = 0
    lodging_db = costs.get("lodging_per_night", {})
    total_nights = max(1, route.days - 1)  # e.g. 7-day trip = 6 nights
    n_dests = max(1, len(route.destinations))
    # Proportionally allocate nights across destinations
    base_nights_per_dest, extra_nights = divmod(total_nights, n_dests)
    for i, dest_id in enumerate(route.destinations):
        region = _region_for_destination(dest_id)
        region_rates = lodging_db.get(region, {})
        season_rates = region_rates.get(season, {})
        nightly = season_rates.get(quality_tier, season_rates.get("mid", 5000))
        dest_nights = base_nights_per_dest + (1 if i < extra_nights else 0)
        lodging_total += nightly * dest_nights

    # --- Food --------------------------------------------------------------
    food_db = costs.get("food_per_person_per_day", {})
    food_daily = food_db.get(quality_tier, food_db.get("mid", 1800))
    food_total = food_daily * query.group_size * route.days

    # --- Activities --------------------------------------------------------
    activities_db = costs.get("activities_per_day", {})
    activities_daily = activities_db.get(quality_tier, activities_db.get("mid", 1500))
    activities_total = activities_daily * query.group_size * route.days

    # --- Buffer ------------------------------------------------------------
    subtotal = transport_total + lodging_total + food_total + activities_total
    buffer_pct = costs.get("buffer_pct", 0.10)
    buffer_total = int(subtotal * buffer_pct)

    total = subtotal + buffer_total

    return CostBreakdown(
        transport=transport_total,
        lodging=lodging_total,
        food=food_total,
        activities=activities_total,
        buffer=buffer_total,
        total=total,
    )


__all__ = ["estimate_cost"]
