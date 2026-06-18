"""
Recommender pipeline — Phase 2 (real).

Replaces the Phase-1 stub. The full flow is:

    filter → enumerate → score (CBR + content + hybrid) → MMR-diversity

If the strict pass yields fewer than 3 candidates, the constraint-relaxation
loop tries successively looser queries and surfaces the first relaxation
note that produced results — the recommender does NOT fail silently.

Public API is unchanged from Phase 1: `recommend(query) -> List[RouteCandidate]`.
"""

from __future__ import annotations

from typing import Dict, List

from manzil.data_loader import load_case_base, load_destinations
from manzil.recommender import cbr, content, diversity, relaxation
from manzil.recommender.enumerate import EnumeratedRoute, enumerate_routes
from manzil.recommender.filter import filter_destinations
from manzil.recommender.hybrid import hybrid_score
from manzil.schemas import (
    CandidateTrace,
    CBRTopKCase,
    CBRTrace,
    CaseBaseEntry,
    ContentTagVector,
    ContentTrace,
    Destination,
    DiversityTrace,
    EnumerateTrace,
    FilterTrace,
    HybridTrace,
    MMRStep,
    RecommendationTrace,
    RouteCandidate,
    TravelMode,
    UserQuery,
)
from manzil.tools.cost_calc import estimate_cost as _full_estimate_cost


def recommend(query: UserQuery) -> List[RouteCandidate]:
    """
    Return exactly 3 diverse candidate routes, or fewer if even the relaxed
    pipeline produces nothing. Each candidate carries `diversity_axes` tags
    and a rationale string. Relaxed runs add a note to the rationale.
    """
    candidates, _ = recommend_with_trace(query)
    return candidates


def recommend_with_trace(
    query: UserQuery,
) -> tuple[List[RouteCandidate], RecommendationTrace]:
    """
    Return 3 diverse candidates plus a full transparency trace of how
    they were selected (filter, enumerate, CBR, content, hybrid, MMR).
    """
    destinations = load_destinations()
    case_base = load_case_base()

    trace = RecommendationTrace()

    # Strict pass
    strict, strict_trace = _try_recommend(query, destinations, case_base)
    if len(strict) >= 3:
        return strict, strict_trace

    # Relaxation passes — yield successively looser queries
    for step in relaxation.relax(query):
        relaxed, relaxed_trace = _try_recommend(step.query, destinations, case_base)
        if len(relaxed) >= 3:
            for cand in relaxed:
                cand.rationale = f"⚠ {step.note}\n\n{cand.rationale}"
            relaxed_trace.relaxation_note = step.note
            return relaxed, relaxed_trace
        if relaxed and len(relaxed) > len(strict):
            strict = relaxed
            strict_trace = relaxed_trace
            for cand in strict:
                cand.rationale = f"⚠ {step.note}\n\n{cand.rationale}"
            strict_trace.relaxation_note = step.note

    return strict, strict_trace


# ---------------------------------------------------------------------------
# Strict-pass implementation (used for both the strict run and each
# relaxation step)
# ---------------------------------------------------------------------------


def _try_recommend(
    query: UserQuery,
    destinations: Dict[str, Destination],
    case_base: List[CaseBaseEntry],
) -> tuple[List[RouteCandidate], RecommendationTrace]:
    fr = filter_destinations(query, destinations)
    filter_trace = FilterTrace(
        total_destinations=len(destinations),
        feasible_count=len(fr.feasible),
        dropped_count=len(fr.dropped),
        dropped_summary={},
    )
    for d in fr.dropped:
        filter_trace.dropped_summary[d.code] = filter_trace.dropped_summary.get(d.code, 0) + 1

    if not fr.feasible:
        return [], RecommendationTrace(filter=filter_trace)

    routes = enumerate_routes(list(fr.feasible.keys()))
    single_stop = sum(1 for r in routes if r.n_stops == 1)
    multi_stop = len(routes) - single_stop
    enum_trace = EnumerateTrace(
        total_routes_generated=len(routes),
        single_stop_routes=single_stop,
        multi_stop_routes=multi_stop,
    )

    if not routes:
        return [], RecommendationTrace(filter=filter_trace, enumerate=enum_trace)

    scored: List[RouteCandidate] = []
    candidate_traces: List[CandidateTrace] = []
    for i, r in enumerate(routes):
        cbr_s, cbr_trace = cbr.score_route(
            r.destinations, query, case_base, return_trace=True
        )
        content_s, content_trace = content.score_route(
            r.destinations, query, destinations, return_trace=True
        )
        cost = _estimate_cost(r, query, destinations)
        axes = diversity.compute_axes(r.destinations, query, destinations, cost)
        hybrid_s = hybrid_score(cbr_s, content_s)

        cand_trace = CandidateTrace(
            candidate_id=f"cand-{i}",
            candidate_label=_label_for(r.destinations, axes, destinations),
            destinations=r.destinations,
            cbr=cbr_trace,
            content=content_trace,
            hybrid=HybridTrace(
                alpha=0.6,
                cbr_score=round(cbr_s, 3),
                content_score=round(content_s, 3),
                hybrid_score=round(hybrid_s, 3),
            ),
            diversity=DiversityTrace(axes=axes),
        )
        candidate_traces.append(cand_trace)

        scored.append(
            RouteCandidate(
                candidate_id=f"cand-{i}",
                label=_label_for(r.destinations, axes, destinations),
                destinations=r.destinations,
                travel_modes=_modes_for(r, query),
                estimated_cost=cost,
                days=query.days,
                diversity_axes=axes,
                cbr_score=cbr_s,
                content_score=content_s,
                rationale=_rationale_for(cbr_s, content_s, axes, case_base),
                rs_trace=cand_trace,
            )
        )

    picked, mmr_steps = diversity.pick_diverse_three(scored, return_trace=True)
    # Reassign clean A/B/C ids for the UI and update traces
    final_traces: List[CandidateTrace] = []
    for letter, cand in zip("ABC", picked):
        cand.candidate_id = f"cand-{letter}"
        if cand.rs_trace:
            cand.rs_trace.candidate_id = f"cand-{letter}"
            cand.rs_trace.candidate_label = cand.label
            final_traces.append(cand.rs_trace)

    # Attach MMR steps to each candidate's diversity trace
    for step in mmr_steps:
        for ct in final_traces:
            if ct.candidate_id == step.candidate_id:
                ct.diversity.mmr_steps = [step]

    rec_trace = RecommendationTrace(
        filter=filter_trace,
        enumerate=enum_trace,
        candidates=final_traces,
    )

    return picked, rec_trace


# ---------------------------------------------------------------------------
# Cost estimate (used for diversity-axis tagging; Phase 3 BudgetAgent does
# the proper decomposition for the debate scoring)
# ---------------------------------------------------------------------------


def _estimate_cost(
    route: EnumeratedRoute,
    query: UserQuery,
    destinations: Dict[str, Destination],
) -> int:
    """
    Delegate to the same cost model the BudgetAgent uses so the
    recommender's estimated_cost and the agent's breakdown are consistent.
    """
    if not route.destinations:
        return 0
    temp = RouteCandidate(
        candidate_id="temp",
        label="",
        destinations=route.destinations,
        travel_modes=_modes_for(route, query),
        estimated_cost=0,
        days=query.days,
    )
    return _full_estimate_cost(temp, query).total


# ---------------------------------------------------------------------------
# Travel modes — one entry per inter-stop segment
# ---------------------------------------------------------------------------


def _modes_for(route: EnumeratedRoute, query: UserQuery) -> List[TravelMode]:
    # In Phase 2 we tile the user's preference across all segments. Phase 3
    # could vary per-segment based on what's actually feasible.
    return [query.travel_mode_pref] * max(1, len(route.destinations))


# ---------------------------------------------------------------------------
# Cosmetic helpers — label and rationale strings for the UI
# ---------------------------------------------------------------------------


_BUDGET_POSTURE_LABEL = {
    "at-budget": "within budget",
    "near-budget": "close to budget",
    "budget-stretch": "budget-stretch",
}


def _label_for(
    route: List[str],
    axes: Dict[str, str],
    destinations: Dict[str, Destination],
) -> str:
    if not route:
        return "(empty route)"
    names = [destinations[d].name.split(",")[0] for d in route if d in destinations]
    body = " + ".join(names) if len(names) <= 3 else f"{names[0]} + {len(names)-1} more"
    posture = _BUDGET_POSTURE_LABEL.get(axes.get("budget_posture", ""), "")
    pace = axes.get("pace", "")
    suffix_bits = [b for b in (pace, posture) if b]
    suffix = f" ({', '.join(suffix_bits)})" if suffix_bits else ""
    return body + suffix


def _rationale_for(
    cbr_s: float,
    content_s: float,
    axes: Dict[str, str],
    case_base: List[CaseBaseEntry],
) -> str:
    h = hybrid_score(cbr_s, content_s)
    bits = [
        f"Hybrid fit score {h:.2f} (CBR {cbr_s:.2f} · style {content_s:.2f}).",
        f"Profile: {axes.get('scope', '?')}, {axes.get('pace', '?')} pace, "
        f"{axes.get('risk', '?')} risk.",
    ]
    if cbr_s > 0.6 and case_base:
        bits.append(
            f"Similar travellers in our case base "
            f"({len(case_base)} cases) rated routes like this highly."
        )
    return " ".join(bits)


__all__ = ["recommend", "recommend_with_trace"]
