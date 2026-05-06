"""
The debate state machine — Phase 3 parallel version.

Topology:
    START -> fan_out -> {Weather, Road, Safety, Budget, Local} -> collect_args -> orchestrator -> END

The 5 agent nodes run in parallel; collect_args is a join.

RPM throttle: if we detect we might exceed Flash-Lite's 15 RPM,
we fall back to sequential execution without changing the public contract.

Public entry point: run_debate(query, candidates) -> DebateResult
"""

from __future__ import annotations

import time
from operator import add
from typing import Annotated, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from manzil.agents.base import set_full_llm_mode
from manzil.agents.budget import BudgetAgent
from manzil.agents.local import LocalExperienceAgent
from manzil.agents.orchestrator import Orchestrator
from manzil.agents.road import RoadAgent
from manzil.agents.safety import SafetyAgent
from manzil.agents.weather import WeatherAgent
from manzil.schemas import (
    AgentArgument,
    DebateResult,
    RouteCandidate,
    UserQuery,
)

# Flash-Lite RPM limit (free tier)
_FLASH_LITE_RPM = 15


class DebateState(TypedDict):
    query: UserQuery
    candidates: List[RouteCandidate]
    # `Annotated[..., add]` makes each node's returned list append-merge into
    # the state instead of replacing it — works for both sequential and parallel.
    arguments: Annotated[List[AgentArgument], add]
    result: Optional[DebateResult]


# ---------------------------------------------------------------------------
# RPM tracking (simple in-memory)
# ---------------------------------------------------------------------------

_rpm_timestamps: List[float] = []


def _rpm_ok(n_calls: int = 5) -> bool:
    """Check if we can make n_calls without exceeding 15 RPM."""
    now = time.time()
    # Clean old timestamps (> 60 seconds)
    global _rpm_timestamps
    _rpm_timestamps = [t for t in _rpm_timestamps if now - t < 60.0]
    return len(_rpm_timestamps) + n_calls <= _FLASH_LITE_RPM


def _record_calls(n_calls: int = 5) -> None:
    now = time.time()
    for _ in range(n_calls):
        _rpm_timestamps.append(now)


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def _make_agent_node(agent_factory):
    def _node(state: DebateState) -> dict:
        agent = agent_factory()
        new_args = [
            agent.evaluate(c, state["query"]) for c in state["candidates"]
        ]
        return {"arguments": new_args}

    return _node


def _orchestrator_node(state: DebateState) -> dict:
    orch = Orchestrator()
    result = orch.synthesize(state["candidates"], state["arguments"])
    return {"result": result}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def _build_graph_parallel():
    """Parallel topology: START -> all 5 agents -> orchestrator -> END."""
    graph = StateGraph(DebateState)

    graph.add_node("weather", _make_agent_node(WeatherAgent))
    graph.add_node("road", _make_agent_node(RoadAgent))
    graph.add_node("safety", _make_agent_node(SafetyAgent))
    graph.add_node("budget", _make_agent_node(BudgetAgent))
    graph.add_node("local", _make_agent_node(LocalExperienceAgent))
    graph.add_node("orchestrator", _orchestrator_node)

    # Parallel fan-out from START
    for name in ("weather", "road", "safety", "budget", "local"):
        graph.add_edge(START, name)

    # Join: all agents -> orchestrator
    for name in ("weather", "road", "safety", "budget", "local"):
        graph.add_edge(name, "orchestrator")

    graph.add_edge("orchestrator", END)

    return graph.compile()


def _build_graph_sequential():
    """Sequential topology for RPM fallback."""
    graph = StateGraph(DebateState)

    graph.add_node("weather", _make_agent_node(WeatherAgent))
    graph.add_node("road", _make_agent_node(RoadAgent))
    graph.add_node("safety", _make_agent_node(SafetyAgent))
    graph.add_node("budget", _make_agent_node(BudgetAgent))
    graph.add_node("local", _make_agent_node(LocalExperienceAgent))
    graph.add_node("orchestrator", _orchestrator_node)

    graph.add_edge(START, "weather")
    graph.add_edge("weather", "road")
    graph.add_edge("road", "safety")
    graph.add_edge("safety", "budget")
    graph.add_edge("budget", "local")
    graph.add_edge("local", "orchestrator")
    graph.add_edge("orchestrator", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_debate(
    query: UserQuery,
    candidates: List[RouteCandidate],
    use_full_llm: bool = False,
) -> DebateResult:
    """
    Run the full debate over the given candidates and return the final
    `DebateResult`. This is what the UI calls.

    Args:
        use_full_llm: If True, each agent calls the LLM to generate unique
            prose (16 calls/debate). If False, agents use templated arguments
            and only the orchestrator calls the LLM (1 call/debate).
    """
    set_full_llm_mode(use_full_llm)

    # Decide parallel vs sequential based on RPM at invocation time
    if _rpm_ok(n_calls=5):
        graph = _build_graph_parallel()
        _record_calls(n_calls=5)
    else:
        graph = _build_graph_sequential()
        _record_calls(n_calls=5)

    initial: DebateState = {
        "query": query,
        "candidates": candidates,
        "arguments": [],
        "result": None,
    }
    final = graph.invoke(initial)
    return final["result"]


__all__ = ["DebateState", "run_debate"]
