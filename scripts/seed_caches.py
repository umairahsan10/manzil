"""
Pre-warm `.manzil_cache/` for the 6-step demo flow + 2 backup queries.

After running this, the entire demo runs with `MANZIL_DEMO_MODE=1` and
zero outbound calls. Run before demo day:

    python scripts/seed_caches.py

This script walks through:
    1. Form submission (recommender)
    2. Agent debate (all 5 agents + orchestrator)
    3. Replan with a disruption
    4. Feedback submission
    5. Second similar query (to test memory loop)
    6. One backup query
    7. Another backup query
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Ensure cache is enabled but NOT in demo mode (we need to make calls)
os.environ.setdefault("MANZIL_USE_CACHE", "1")
os.environ.pop("MANZIL_DEMO_MODE", None)

from manzil.agents.base import set_full_llm_mode
from manzil.graph.debate_graph import run_debate
from manzil.memory.feedback import submit_feedback
from manzil.recommender.pipeline import recommend
from manzil.replan import replan
from manzil.schemas import (
    Disruption,
    GroupType,
    TravelMode,
    UserQuery,
)
from manzil.tools.cache import is_demo_mode


def _step(label: str):
    print(f"  [{label}]")


def seed():
    print("Seeding caches for demo mode...")

    # Ensure we're not in demo mode (we need live calls to populate cache)
    if is_demo_mode():
        print("ERROR: MANZIL_DEMO_MODE is set. Unset it before seeding.")
        sys.exit(1)

    # Use efficient mode (templated arguments, only orchestrator LLM call)
    set_full_llm_mode(False)

    print("\nStep 1: Form submission — recommender")
    query_1 = UserQuery(
        group_size=4,
        group_composition=GroupType.FRIENDS,
        budget_pkr=120_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural", "photography"],
        difficulty_tolerance=3,
    )
    candidates_1 = recommend(query_1)
    _step(f"recommender returned {len(candidates_1)} candidates")

    print("\nStep 2: Agent debate")
    result_1 = run_debate(query_1, candidates_1)
    winner_1 = result_1.winner
    _step(f"debate done, winner={winner_1.candidate_id if winner_1 else 'NONE'}")

    print("\nStep 3: Replan with road closure disruption")
    disruption = Disruption(
        kind="road_closed",
        pass_id="babusar",
        day_index=3,
        description="Babusar Pass closed due to landslide",
    )
    replan_result = replan(query_1, disruption)
    _step(f"replan done, winner={replan_result.winner.candidate_id if replan_result.winner else 'NONE'}")

    print("\nStep 4: Feedback submission")
    if winner_1:
        entry = submit_feedback(
            query=query_1,
            winner_route=winner_1.destinations,
            travel_modes=[tm.value for tm in winner_1.travel_modes],
            rating=4.0,
            tags=["loved-the-food", "great-views"],
        )
        _step(f"feedback submitted, case_id={entry.case_id}")
    else:
        _step("no winner to submit feedback for")

    print("\nStep 5: Second similar query (memory loop)")
    query_2 = UserQuery(
        group_size=3,
        group_composition=GroupType.FRIENDS,
        budget_pkr=110_000,
        days=6,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="karachi",
        style_tags=["cultural", "photography"],
        difficulty_tolerance=3,
    )
    candidates_2 = recommend(query_2)
    result_2 = run_debate(query_2, candidates_2)
    _step(f"similar query: {len(candidates_2)} candidates, winner={result_2.winner.candidate_id if result_2.winner else 'NONE'}")

    print("\nStep 6: Backup query — family")
    query_3 = UserQuery(
        group_size=4,
        group_composition=GroupType.FAMILY,
        budget_pkr=150_000,
        days=5,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="islamabad",
        style_tags=["family", "relaxation"],
        difficulty_tolerance=2,
    )
    candidates_3 = recommend(query_3)
    result_3 = run_debate(query_3, candidates_3)
    _step(f"backup family: {len(candidates_3)} candidates, winner={result_3.winner.candidate_id if result_3.winner else 'NONE'}")

    print("\nStep 7: Backup query — solo adventure")
    query_4 = UserQuery(
        group_size=1,
        group_composition=GroupType.SOLO,
        budget_pkr=80_000,
        days=7,
        travel_month=7,
        travel_mode_pref=TravelMode.ROAD,
        origin_city="lahore",
        style_tags=["adventure", "photography"],
        difficulty_tolerance=4,
    )
    candidates_4 = recommend(query_4)
    result_4 = run_debate(query_4, candidates_4)
    _step(f"backup solo: {len(candidates_4)} candidates, winner={result_4.winner.candidate_id if result_4.winner else 'NONE'}")

    print("\n✅ Cache seeding complete.")
    print("Set MANZIL_DEMO_MODE=1 and run streamlit to verify zero outbound calls.")


if __name__ == "__main__":
    seed()
