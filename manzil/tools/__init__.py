from manzil.tools.cache import CacheMiss, get, is_demo_mode, set, stable_key
from manzil.tools.cost_calc import estimate_cost
from manzil.tools.route_calc import (
    drive_time,
    landslide_risk_for_month,
    max_single_leg_drive_time,
    passes_on_route,
    route_segments,
    total_drive_time,
)
from manzil.tools.weather_api import WeatherError, get_forecast, healthcheck

try:
    from manzil.tools.rag import add_documents, retrieve
except ImportError:
    retrieve = None  # type: ignore
    add_documents = None  # type: ignore

__all__ = [
    "CacheMiss",
    "get",
    "is_demo_mode",
    "set",
    "stable_key",
    "estimate_cost",
    "drive_time",
    "landslide_risk_for_month",
    "max_single_leg_drive_time",
    "passes_on_route",
    "route_segments",
    "total_drive_time",
    "WeatherError",
    "get_forecast",
    "healthcheck",
    "retrieve",
    "add_documents",
]
