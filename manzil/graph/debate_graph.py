"""
The debate state machine.

Phase 1: sequential — START → 5 agents in series → orchestrator → END.
Phase 3: parallel — START → 5 agents in parallel → join → orchestrator → END.

The contract from the UI's perspective is just `run_debate(query, candidates)`.

Note: LangGraph 0.2 requires every node to write to at least one state channel.
A `fan_out` no-op node (returning `{}`) raises `InvalidUpdateError`. So in
Phase 1 we just edge `START` directly into the first agent. Phase 3 will
add parallel edges from `START` to all five agent nodes.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

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


class DebateState(TypedDict):
    query: UserQuery
    candidates: List[RouteCandidate]
    # `Annotated[..., add]` makes each node's returned list append-merge into
    # the state instead of replacing it — works for both sequential (Phase 1)
    # and parallel (Phase 3) execution.
    arguments: Annotated[List[AgentArgument], add]
    result: Optional[DebateResult]


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


def _build_graph():
    graph = StateGraph(DebateState)

    graph.add_node("weather", _make_agent_node(WeatherAgent))
    graph.add_node("road", _make_agent_node(RoadAgent))
    graph.add_node("safety", _make_agent_node(SafetyAgent))
    graph.add_node("budget", _make_agent_node(BudgetAgent))
    graph.add_node("local", _make_agent_node(LocalExperienceAgent))
    graph.add_node("orchestrator", _orchestrator_node)

    # Sequential in Phase 1. Phase 3 swaps to parallel fan-out: edge from
    # START to each of the 5 agent nodes, then a join node before orchestrator.
    graph.add_edge(START, "weather")
    graph.add_edge("weather", "road")
    graph.add_edge("road", "safety")
    graph.add_edge("safety", "budget")
    graph.add_edge("budget", "local")
    graph.add_edge("local", "orchestrator")
    graph.add_edge("orchestrator", END)

    return graph.compile()


_GRAPH = None


def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_debate(
    query: UserQuery, candidates: List[RouteCandidate]
) -> DebateResult:
    """
    Run the full debate over the given candidates and return the final
    `DebateResult`. This is what the UI calls.
    """
    initial: DebateState = {
        "query": query,
        "candidates": candidates,
        "arguments": [],
        "result": None,
    }
    final = _graph().invoke(initial)
    return final["result"]


__all__ = ["DebateState", "run_debate"]
