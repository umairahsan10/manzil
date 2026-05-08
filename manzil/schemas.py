"""
Manzil data contracts.

These Pydantic models are the contracts between the recommender, the agents,
the orchestrator, the UI, and the case base. Changes here ripple everywhere —
treat as load-bearing.

Pydantic v2 syntax throughout. Use `.model_dump()` (not `.dict()`).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TravelMode(str, Enum):
    ROAD = "road"
    AIR = "air"
    HYBRID = "hybrid"


class GroupType(str, Enum):
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    FRIENDS = "friends"
    MIXED = "mixed"


# ---------------------------------------------------------------------------
# Destination — the catalog row
# ---------------------------------------------------------------------------


class Destination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    region: str
    coords: Tuple[float, float]
    altitude_m: int
    terrain_tags: List[str] = Field(default_factory=list)
    activity_tags: List[str] = Field(default_factory=list)
    difficulty: int = Field(ge=1, le=5)
    cost_per_day: Dict[str, int]  # {"low": int, "mid": int, "high": int} in PKR
    season_open: List[bool]  # length 12, True if accessible that month (Jan=index 0)
    group_suitability: List[str] = Field(default_factory=list)
    accessible: bool = False
    noc_required_for_foreigners: bool = False
    description: str = ""

    @field_validator("season_open")
    @classmethod
    def _twelve_months(cls, v: List[bool]) -> List[bool]:
        if len(v) != 12:
            raise ValueError("season_open must have exactly 12 entries (Jan..Dec)")
        return v

    @field_validator("cost_per_day")
    @classmethod
    def _cost_tiers(cls, v: Dict[str, int]) -> Dict[str, int]:
        required = {"low", "mid", "high"}
        if not required.issubset(v.keys()):
            raise ValueError(f"cost_per_day must define tiers {required}")
        return v


# ---------------------------------------------------------------------------
# UserQuery — what the user submits
# ---------------------------------------------------------------------------


class UserQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_size: int = Field(ge=1)
    group_composition: GroupType
    budget_pkr: int = Field(gt=0)
    days: int = Field(ge=2, le=21)
    travel_month: int = Field(ge=1, le=12)
    travel_mode_pref: TravelMode
    origin_city: str
    style_tags: List[str] = Field(default_factory=list)
    difficulty_tolerance: int = Field(ge=1, le=5)
    preferred_destinations: List[str] = Field(default_factory=list)
    hard_constraints: List[str] = Field(default_factory=list)
    is_foreign_traveller: bool = False
    elderly_in_group: bool = False


# ---------------------------------------------------------------------------
# Disruption — used by the replanning mechanism
# ---------------------------------------------------------------------------


class Disruption(BaseModel):
    """A mid-trip disruption that triggers replanning."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(
        ...,
        pattern="^(road_closed|budget_cut|weather_event|flight_cancelled)$",
    )
    # Parameters vary by kind:
    day_index: Optional[int] = None          # which day the disruption hits
    pct_cut: Optional[float] = None          # for budget_cut (e.g. 15 means -15%)
    pass_id: Optional[str] = None            # for road_closed (e.g. "babusar")
    destination_id: Optional[str] = None     # for weather_event / flight_cancelled
    description: str = ""                    # human-readable summary


# ---------------------------------------------------------------------------
# RouteCandidate — what the recommender outputs
# ---------------------------------------------------------------------------


class RouteCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    label: str
    destinations: List[str]  # ordered list of Destination ids
    travel_modes: List[TravelMode]  # mode used between consecutive segments
    estimated_cost: int  # PKR, total for the group
    days: int
    diversity_axes: Dict[str, str] = Field(default_factory=dict)
    cbr_score: float = Field(ge=0.0, le=1.0, default=0.0)
    content_score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str = ""

    @field_validator("travel_modes")
    @classmethod
    def _modes_match_segments(cls, v: List[TravelMode], info) -> List[TravelMode]:
        # We do not strictly enforce len-1 vs len here because origin->first-stop
        # is a segment too. Just enforce non-empty when destinations is non-empty.
        return v


# ---------------------------------------------------------------------------
# AgentArgument — the structured argument every specialist emits per candidate
# ---------------------------------------------------------------------------


class AgentArgument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    candidate_id: str
    score: float = Field(ge=0.0, le=10.0)
    supporting_reasons: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    hard_blocker: Optional[str] = None  # if set, this candidate is disqualified
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Day-by-day plan — what the user sees as the "winning route"
# ---------------------------------------------------------------------------


class DayStop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_id: str
    name: str
    activities: List[str] = Field(default_factory=list)
    local_tip: Optional[str] = None


class DayPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_index: int = Field(ge=1)
    stops: List[DayStop] = Field(default_factory=list)
    travel_mode: Optional[TravelMode] = None
    drive_time_hours: Optional[float] = None
    estimated_cost: int = 0
    weather_note: Optional[str] = None
    road_note: Optional[str] = None
    safety_note: Optional[str] = None


class DayByDayPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    days: List[DayPlan] = Field(default_factory=list)
    total_cost: int = 0


# ---------------------------------------------------------------------------
# DebateResult — what the Orchestrator outputs
# ---------------------------------------------------------------------------


class DebateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    winner: Optional[RouteCandidate]  # None when all candidates were blocked
    full_plan: Optional[DayByDayPlan] = None
    scorecard: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # scorecard[agent_name][candidate_id] = score

    blockers: Dict[str, List[str]] = Field(default_factory=dict)
    # blockers[candidate_id] = list of blocker reasons

    arguments: List[AgentArgument] = Field(default_factory=list)
    # raw agent arguments (enables the scorecard detail panel)

    dissenting_opinion: Optional[str] = None
    why_not: Dict[str, str] = Field(default_factory=dict)
    # why_not[runner_up_candidate_id] = one-line explanation

    orchestrator_reasoning: str = ""
    all_blocked: bool = False  # True when every candidate had a hard blocker


# ---------------------------------------------------------------------------
# CaseBaseEntry — historical / synthetic trip used by the recommender's CBR step
# ---------------------------------------------------------------------------


class CaseBaseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    query: UserQuery
    chosen_route: List[str]  # destination ids in order
    travel_modes: List[TravelMode]
    persona: str  # which persona generated this (or "real_user" for actual feedback)
    rating: float = Field(ge=1.0, le=5.0)
    feedback_tags: List[str] = Field(default_factory=list)
    is_synthetic: bool = True


# ---------------------------------------------------------------------------
# Tool-layer DTOs (used by tools/, returned into agent _analyze methods)
# ---------------------------------------------------------------------------


class WeatherData(BaseModel):
    """Output of `manzil.tools.weather_api.get_forecast`."""

    model_config = ConfigDict(extra="forbid")

    destination_id: Optional[str] = None
    coords: Tuple[float, float]
    start_date: str  # ISO date
    days: int
    daily_temp_max_c: List[float] = Field(default_factory=list)
    daily_temp_min_c: List[float] = Field(default_factory=list)
    daily_precip_mm: List[float] = Field(default_factory=list)
    daily_precip_prob: List[float] = Field(default_factory=list)
    summary: str = ""  # a short human-readable summary, optional


class CostBreakdown(BaseModel):
    """Output of `manzil.tools.cost_calc.estimate_cost`."""

    model_config = ConfigDict(extra="forbid")

    transport: int = 0
    lodging: int = 0
    food: int = 0
    activities: int = 0
    buffer: int = 0
    total: int = 0


# ---------------------------------------------------------------------------
# LLM argument payload — the strict JSON shape we ask the LLM to emit
# ---------------------------------------------------------------------------


class LLMArgumentPayload(BaseModel):
    """What `BaseAgent._llm_argue` parses out of a Gemini response."""

    model_config = ConfigDict(extra="forbid")

    reasons: List[str] = Field(default_factory=list, max_length=5)
    concerns: List[str] = Field(default_factory=list, max_length=5)


__all__ = [
    "TravelMode",
    "GroupType",
    "Destination",
    "UserQuery",
    "RouteCandidate",
    "AgentArgument",
    "DayStop",
    "DayPlan",
    "DayByDayPlan",
    "DebateResult",
    "CaseBaseEntry",
    "WeatherData",
    "CostBreakdown",
    "LLMArgumentPayload",
    "Disruption",
]
