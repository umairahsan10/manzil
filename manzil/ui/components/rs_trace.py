"""
Recommender system trace component — step-by-step transparency.

Shows how the 3 candidate routes were selected, with real computed data:
1. Hard-constraint filter
2. Route enumeration (BFS)
3. CBR scoring with top-k cases table
4. Content scoring with tag vectors
5. Hybrid blending
6. Diversity axes
7. Greedy MMR selection

Uses session_state to avoid re-animating on reruns.
"""

from __future__ import annotations

import time
from typing import List

import streamlit as st

from manzil.schemas import (
    CandidateTrace,
    CBRTopKCase,
    ContentTagVector,
    MMRStep,
    RecommendationTrace,
)

STEP_TITLES = [
    "Step 1 — Hard-Constraint Filter",
    "Step 2 — Route Enumeration (BFS)",
    "Step 3 — CBR Scoring",
    "Step 4 — Content-Based Scoring",
    "Step 5 — Hybrid Score",
    "Step 6 — Diversity Axes",
    "Step 7 — Greedy MMR Selection",
]

STEP_DESCS = [
    "Destinations that violate hard constraints are dropped before any routes are built.",
    "Ordered destination chains are built with BFS, pruning impractical legs.",
    "Finds past travellers similar to you who visited overlapping destinations.",
    "Measures how well the route's tags match your style preferences.",
    "Blends historical evidence (CBR) with preference matching (content).",
    "Tags each route on 5 observable dimensions to avoid near-identical options.",
    "Picks 3 routes that are both high-scoring and genuinely different.",
]


def render_rs_trace(trace: RecommendationTrace) -> None:
    """
    Render the recommender system trace as an animated step-by-step reveal.
    """
    if not trace or not trace.candidates:
        return

    state_key = "rs_trace_done"
    if st.session_state.get(state_key):
        _render_static_rs_trace(trace)
        return

    st.markdown("#### How these 3 routes were selected")
    st.caption("A step-by-step breakdown of the recommender system's decisions.")

    placeholder = st.empty()
    shown_steps: List[str] = []

    # Step 1: Filter
    _step_filter(shown_steps, trace, placeholder)
    time.sleep(0.4)

    # Step 2: Enumerate
    _step_enumerate(shown_steps, trace, placeholder)
    time.sleep(0.4)

    # Step 3-7: Per-candidate scoring (show all 3 candidates together per step)
    for step_idx in range(3, 8):
        _step_candidate_math(step_idx, shown_steps, trace, placeholder)
        time.sleep(0.4)

    st.session_state[state_key] = True
    placeholder.empty()
    _render_static_rs_trace(trace)


def _step_filter(shown_steps: List[str], trace: RecommendationTrace, placeholder) -> None:
    f = trace.filter_
    lines = [
        f"**{STEP_TITLES[0]}**",
        f"{STEP_DESCS[0]}",
        "",
        f"- Total destinations in catalog: **{f.total_destinations}**",
        f"- Passed filter (feasible): **{f.feasible_count}**",
        f"- Dropped: **{f.dropped_count}**",
    ]
    if f.dropped_summary:
        lines.append("- Breakdown:")
        for code, count in f.dropped_summary.items():
            lines.append(f"  - `{code}`: {count}")
    shown_steps.append("<br>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_enumerate(shown_steps: List[str], trace: RecommendationTrace, placeholder) -> None:
    e = trace.enumerate_
    lines = [
        f"**{STEP_TITLES[1]}**",
        f"{STEP_DESCS[1]}",
        "",
        f"- Max destinations per chain: **{e.max_destinations}**",
        f"- Max single-leg drive: **{e.max_single_leg_hours}h**",
        f"- Route cap: **{e.max_routes_cap}**",
        f"- Total routes generated: **{e.total_routes_generated}**",
        f"  - Single-stop: **{e.single_stop_routes}**",
        f"  - Multi-stop: **{e.multi_stop_routes}**",
    ]
    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _step_candidate_math(
    step_idx: int,
    shown_steps: List[str],
    trace: RecommendationTrace,
    placeholder,
) -> None:
    title = STEP_TITLES[step_idx - 1]
    desc = STEP_DESCS[step_idx - 1]
    lines = [f"**{title}**", f"{desc}", ""]

    for cand in trace.candidates:
        lines.append(f"**{cand.candidate_label}** (`{cand.candidate_id}`)")
        if step_idx == 3:
            lines.extend(_format_cbr(cand.cbr))
        elif step_idx == 4:
            lines.extend(_format_content(cand.content))
        elif step_idx == 5:
            lines.extend(_format_hybrid(cand.hybrid))
        elif step_idx == 6:
            lines.extend(_format_axes(cand.diversity.axes))
        elif step_idx == 7:
            lines.extend(_format_mmr(cand.diversity.mmr_steps))
        lines.append("")

    shown_steps.append("<hr>".join(lines))
    placeholder.markdown("<hr>".join(shown_steps), unsafe_allow_html=True)


def _format_cbr(cbr: CBRTrace) -> List[str]:
    lines = [
        f"- Top **{cbr.k}** most similar past cases:",
    ]
    if cbr.top_cases:
        lines.append(
            "| Case | query_sim | route_overlap | rating | weight (sim×overlap) |"
        )
        lines.append("|---|---|---|---|---|")
        for case in cbr.top_cases:
            lines.append(
                f"| {case.case_id} | {case.query_similarity} | {case.route_overlap} "
                f"| {case.rating} | **{case.weight}** |"
            )
    else:
        lines.append("  *(No overlapping cases found)*")
    lines.append(f"- Weighted average rating: **{cbr.weighted_avg_rating}**")
    lines.append(f"- Normalized CBR score: **{cbr.normalized_score}**")
    return lines


def _format_content(content: ContentTrace) -> List[str]:
    lines = [
        f"- Tag cosine similarity: **{content.tag_cosine}**",
        f"- Difficulty match: **{content.difficulty_match}** "
        f"(avg route difficulty {content.avg_route_difficulty}, tolerance {content.user_tolerance})",
        f"- Content score = 0.7 × {content.tag_cosine} + 0.3 × {content.difficulty_match} = **{content.content_score}**",
    ]
    if content.user_vector:
        # Show only non-zero tags for brevity
        nonzero = [v for v in content.user_vector if v.user_value > 0 or v.route_value > 0]
        if nonzero:
            lines.append("- Tag vectors (non-zero only):")
            lines.append("| Tag | User | Route |")
            lines.append("|---|---|---|")
            for v in nonzero:
                lines.append(f"| {v.tag} | {v.user_value} | {v.route_value} |")
    return lines


def _format_hybrid(hybrid: ContentTrace) -> List[str]:
    return [
        f"- Hybrid = {hybrid.alpha} × CBR + {1 - hybrid.alpha} × Content",
        f"- Hybrid = {hybrid.alpha} × {hybrid.cbr_score} + {1 - hybrid.alpha} × {hybrid.content_score}",
        f"- **Hybrid score: {hybrid.hybrid_score}**",
    ]


def _format_axes(axes: dict) -> List[str]:
    return [f"- `{k}`: **{v}**" for k, v in axes.items()]


def _format_mmr(mmr_steps: List[MMRStep]) -> List[str]:
    if not mmr_steps:
        return ["- *(No MMR data)*"]
    lines = []
    for step in mmr_steps:
        lines.append(
            f"- Step {step.step}: picked `{step.candidate_id}` — "
            f"hybrid {step.hybrid_score}, axis-sim {step.max_axis_similarity_to_picked}, "
            f"MMR = **{step.mmr_score}**"
        )
    return lines


def _render_static_rs_trace(trace: RecommendationTrace) -> None:
    st.markdown("#### How these 3 routes were selected")
    st.caption("A step-by-step breakdown of the recommender system's decisions.")

    # Use expanders for a cleaner static view
    with st.expander(STEP_TITLES[0], expanded=False):
        f = trace.filter_
        st.markdown(f"- Total destinations: **{f.total_destinations}**")
        st.markdown(f"- Feasible: **{f.feasible_count}**")
        st.markdown(f"- Dropped: **{f.dropped_count}**")
        if f.dropped_summary:
            st.markdown("**Breakdown:**")
            for code, count in f.dropped_summary.items():
                st.markdown(f"- `{code}`: {count}")

    with st.expander(STEP_TITLES[1], expanded=False):
        e = trace.enumerate_
        st.markdown(f"- Max destinations/chain: **{e.max_destinations}**")
        st.markdown(f"- Max leg drive: **{e.max_single_leg_hours}h**")
        st.markdown(f"- Total routes: **{e.total_routes_generated}** (single {e.single_stop_routes}, multi {e.multi_stop_routes})")

    with st.expander(STEP_TITLES[2], expanded=False):
        for cand in trace.candidates:
            st.markdown(f"**{cand.candidate_label}**")
            if cand.cbr.top_cases:
                st.markdown(f"Top {cand.cbr.k} cases (weighted avg rating: {cand.cbr.weighted_avg_rating})")
                data = [
                    {
                        "Case": c.case_id,
                        "query_sim": c.query_similarity,
                        "overlap": c.route_overlap,
                        "rating": c.rating,
                        "weight": c.weight,
                    }
                    for c in cand.cbr.top_cases
                ]
                st.dataframe(data, use_container_width=True, hide_index=True)
            else:
                st.caption("No overlapping cases.")
            st.markdown(f"**CBR score: {cand.cbr.normalized_score}**")
            st.divider()

    with st.expander(STEP_TITLES[3], expanded=False):
        for cand in trace.candidates:
            st.markdown(f"**{cand.candidate_label}**")
            st.markdown(f"Tag cosine: **{cand.content.tag_cosine}**")
            st.markdown(f"Difficulty match: **{cand.content.difficulty_match}**")
            if cand.content.user_vector:
                nonzero = [v for v in cand.content.user_vector if v.user_value > 0 or v.route_value > 0]
                if nonzero:
                    st.dataframe(
                        [{"Tag": v.tag, "User": v.user_value, "Route": v.route_value} for v in nonzero],
                        use_container_width=True,
                        hide_index=True,
                    )
            st.markdown(f"**Content score: {cand.content.content_score}**")
            st.divider()

    with st.expander(STEP_TITLES[4], expanded=False):
        for cand in trace.candidates:
            h = cand.hybrid
            st.markdown(
                f"**{cand.candidate_label}**: "
                f"{h.alpha} × {h.cbr_score} + {1 - h.alpha} × {h.content_score} = **{h.hybrid_score}**"
            )

    with st.expander(STEP_TITLES[5], expanded=False):
        for cand in trace.candidates:
            st.markdown(f"**{cand.candidate_label}**")
            for k, v in cand.diversity.axes.items():
                st.markdown(f"- `{k}`: **{v}**")

    with st.expander(STEP_TITLES[6], expanded=False):
        for cand in trace.candidates:
            for step in cand.diversity.mmr_steps:
                st.markdown(
                    f"**Step {step.step}** → `{step.candidate_id}`: "
                    f"hybrid {step.hybrid_score} − {step.lambda_} × {step.max_axis_similarity_to_picked} = **MMR {step.mmr_score}**"
                )
                st.caption(f"Already picked: {', '.join(step.picked_so_far)}")

    if trace.relaxation_note:
        st.info(f"**Constraint relaxation applied:** {trace.relaxation_note}")


__all__ = ["render_rs_trace"]
