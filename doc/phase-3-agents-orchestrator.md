# Phase 3 — Full Agent Cast + Real Orchestrator

> **Estimated:** Weeks 6–8.
> **Owner-lead:** Person 2 (Agent Lead). Person 3 helps with the RAG corpus
> scrape; Person 1 reviews the policy weights.

## Goal

All 5 specialist agents are real (deterministic analysis + LLM-generated
argument). The Orchestrator implements the section-7 policy: hard-blocker
elimination, weighted aggregation, concentration tie-break, dissent
detection, why-not summaries, and a single Flash synthesis call. LangGraph
fans out the agents in parallel.

By the end of this phase, the **debate is real**.

## Why this phase

Until now we have a working pipeline shape but only one real agent. This
phase is what turns the system from a frame into the thing the readme
promises. It's also where the safety-first commitment shows up in code:
a Safety Agent that can veto a candidate is what differentiates Manzil
from a search box.

## Inputs / preconditions

- Phase 2 verified — recommender returns 3 diverse candidates
- WeatherAgent and `BaseAgent` from Phase 1 in good shape
- Knowledge bases (`road_knowledge.json`, `safety_knowledge.json`,
  `costs.json`) populated for all 10–15 destinations

## Deliverables

### Real agents (Person 2)

#### Road Agent (`manzil/agents/road.py`)

| Method | Behaviour |
|---|---|
| `_analyze` | Look up each pass on the route in `road_knowledge.json`. Compute drive-time per day from the distance matrix. Aggregate landslide risk for the chosen month. |
| `_check_blocker` | **Veto** if any pass on the route has `open_months[query.travel_month-1] is False`. **Veto** if any single day's drive exceeds 12 hours (humane-driving rule). |
| `_score` | Linear from average drive-time per day and aggregate landslide risk. |
| `_llm_argue` | Reasons emphasize "smooth highway segments" / "well-paved KKH"; concerns surface "monsoon landslide history" / "long Day 3 drive". |

#### Safety Agent (`manzil/agents/safety.py`)

| Method | Behaviour |
|---|---|
| `_analyze` | For each destination: altitude, NOC requirement, nearest hospital/police. For the group: altitude tolerance threshold (kids < 10 → 3,000 m; 10–60 → 4,500 m; > 60 → 3,500 m). |
| `_check_blocker` | **Veto** if any destination's altitude exceeds the group's threshold AND the trip lacks an acclimatization day. **Veto** if a foreign-traveller query hits an NOC zone (this catches the wedge-user-not-alone case). |
| `_score` | Penalize altitude headroom narrowness, NOC complexity, distance from medical care. |
| `_llm_argue` | Reasons cite hospital proximity, low-altitude profile; concerns cite altitude exposure, NOC, isolation. |

#### Budget Agent (`manzil/agents/budget.py`)

| Method | Behaviour |
|---|---|
| `_analyze` | Calls `manzil/tools/cost_calc.py:estimate_cost(route, query) -> CostBreakdown`. Decomposes: transport (per segment, per mode, per group size) + lodging (per night, per quality tier) + food + activities + 10% buffer. |
| `_check_blocker` | **Veto** if `total > query.budget_pkr × 1.15` (the relaxation tolerance from Phase 2). |
| `_score` | Linear inverse of cost overshoot, capped at 10 when within budget. |
| `_llm_argue` | Reasons cite "fits comfortably", "transport-light"; concerns cite "lodging at peak season", "guide fees not budgeted". |

#### Local Experience Agent (`manzil/agents/local.py`)

| Method | Behaviour |
|---|---|
| `_analyze` | For each destination, query the RAG index via `manzil/tools/rag.py:retrieve(destination_id, query_text, k=5)`. Aggregate retrieved chunks. |
| `_check_blocker` | **Never blocks** — Local Experience is enrichment, not safety. |
| `_score` | Average retrieval relevance + cultural-alignment score against `query.style_tags`. **If retrieval is empty for any destination, score that segment 0 and lower `confidence`.** |
| `_llm_argue` | Reasons quote/paraphrase from retrieved chunks (food spots, viewpoints, photography hours). **If retrieval is empty, surface the gap honestly: "We don't have curated local content for X yet."** No hallucination. |

### Tooling (Person 2 + Person 3)

| File | Responsibility |
|---|---|
| `manzil/tools/cost_calc.py` | `estimate_cost(route, query) -> CostBreakdown`. Pure Python over `costs.json`. Used by Budget Agent and the Orchestrator's plan expander. |
| `manzil/tools/route_calc.py` | `drive_time(from_id, to_id) -> float`. Pure Python over `road_knowledge.json` distance matrix. |
| `manzil/tools/rag.py` | ChromaDB wrapper. `retrieve(destination_id, query_text, k=5) -> List[Chunk]`. Empty list is a valid response. |
| `scripts/build_rag_index.py` | One-time script: chunk every file in `data/local_corpus/`, embed with Gemini `text-embedding-004`, persist to `chroma_db/`. Idempotent (skips already-indexed files). |
| `data/local_corpus/<dest>/*.md` | ~5–15 curated documents per destination. Pass 1: scrape Wikivoyage + 2–3 reputable Pakistani travel blogs, chunk to ~200 words. Pass 2 in Phase 5 curates based on observed retrieval failures. |

### Orchestrator (Person 2)

| File | Responsibility |
|---|---|
| `manzil/agents/orchestrator.py` | Replace Phase-1 stub. Implements section-7 policy. |

```python
def synthesize(self, candidates, arguments, blockers) -> DebateResult:
    surviving = [c for c in candidates if not blockers.get(c.candidate_id)]
    if not surviving:
        return self._all_blocked_response(candidates, blockers)

    weights = {
        "SafetyAgent":  0.30,
        "BudgetAgent":  0.25,
        "WeatherAgent": 0.20,
        "RoadAgent":    0.15,
        "LocalAgent":   0.10,
    }
    aggregate_scores = self._weighted_aggregate(surviving, arguments, weights)
    winner = self._pick_winner(surviving, aggregate_scores, arguments, eps=0.3)
    dissent = self._detect_dissent(winner, arguments)
    why_not = self._generate_why_not(surviving, winner, arguments)
    reasoning = self._llm_synthesize(winner, arguments, dissent)   # 1 Flash call
    full_plan = self._expand_plan(winner, arguments)
    return DebateResult(...)
```

Tie-break (concentration over breadth):

```python
def _concentration(args_for_candidate):
    scores = [a.score for a in args_for_candidate]
    return max(scores) - min(scores)
# When two are within ε=0.3, pick the one with HIGHER concentration.
```

### LangGraph parallelism (Person 2)

| File | Change |
|---|---|
| `manzil/graph/debate_graph.py` | Replace sequential pass with parallel fan-out via LangGraph conditional edges. Add an internal RPM throttle: if Flash-Lite is at 15 RPM, fall back to sequential without changing the contract. |

Topology unchanged from the tech sketch ASCII diagram:

```
START → fan_out → {Weather, Road, Safety, Budget, Local} → collect_args → orchestrator → END
```

The 5 agent nodes run in parallel; `collect_args` is a join.

### Replanning (Person 2)

Per the proposal (PDF §6, P4), replanning ships with the Multi-Agent
System. The logic lives here in Phase 3; the user-facing side-by-side
comparison UI ships in Phase 4.

| File | Responsibility |
|---|---|
| `manzil/schemas.py` | Add the `Disruption` Pydantic model: `kind` ∈ {`road_closed`, `budget_cut`, `weather_event`, `flight_cancelled`}, plus parameters (`day_index`, `pct_cut`, `pass_id`, etc.). |
| `manzil/replan.py` | `replan(original_query, disruption) -> DebateResult`. Constructs a modified `UserQuery` (e.g., adds the closed pass to a hard-constraint list, trims the budget, shifts dates around a weather event), re-runs the recommender, re-runs the debate, returns the new `DebateResult`. The original is preserved by the caller. |

Why a full re-run rather than incremental adjustment: the debate is cheap
(~16 calls, mostly cached), and small disruptions can have large
consequences (a closed pass eliminates whole routes), so a full re-run
produces more honest results than a patched-up original.

### Tests

| File | Cases |
|---|---|
| `tests/test_orchestrator_policy.py` | Hard-blocker elimination drops vetoed candidates. Weighted aggregation matches a hand-computed example. ε-window tie-break picks the concentrated candidate. Dissent detection: when one agent is >2 points below the consensus, dissent surfaces. |
| `tests/test_all_blocked.py` | A query where every candidate is safety-blocked → `DebateResult(winner=None, all_blocked=True, blockers=...)`. |
| `tests/test_road_agent.py` | Closed pass in chosen month → blocker fires. Drive-time > 12h → blocker fires. |
| `tests/test_safety_agent.py` | Family with kids + Khunjerab in October → blocker. |
| `tests/test_budget_agent.py` | 50% over budget → blocker. Within budget → high score. |
| `tests/test_local_agent.py` | RAG returns empty for a destination → graceful degrade, confidence drops, no hallucinated content in reasons. |
| `tests/test_graph_parallel.py` | Time the graph with 5 agents that each `time.sleep(0.5)`; total runtime < 1 second proves parallelism. |
| `tests/test_replan.py` | Original query → run debate → inject `Disruption(kind="road_closed", day_index=3)` → assert `replan()` returns a `DebateResult` whose `winner.candidate_id` differs from the original (or `all_blocked=True` with a reason citing the closed segment). |

## Order of work

### Week 6 — Road + Safety + Budget

1. Day 1–2: Road Agent + `route_calc.py` + tests
2. Day 3–4: Safety Agent + tests
3. Day 5: Budget Agent + `cost_calc.py` + tests

### Week 7 — RAG + Local Agent

1. Day 1–2: Person 3 scrapes `data/local_corpus/`, chunks to ~200 words
2. Day 3: `manzil/tools/rag.py` + `scripts/build_rag_index.py`
3. Day 4: Local Experience Agent (RAG-grounded, refusal on empty)
4. Day 5: Local Agent tests, sanity-check on retrieved chunks

### Week 8 — Orchestrator + LangGraph parallelism + Replanning

1. Day 1–2: Orchestrator policy (aggregation, blocker elimination,
   tie-break, dissent, why-not)
2. Day 3: LLM synthesis call (`_llm_synthesize`), `_expand_plan` for
   day-by-day plan output
3. Day 4: LangGraph parallel fan-out + RPM throttle
4. Day 5: All-blocked failure mode; replanning logic (`Disruption`
   schema + `manzil/replan.py`); scenario test sweep

## Acceptance criteria

- *"5-day Karachi-to-Skardu road trip in January"* → all 3 candidates have
  Safety Agent blockers → orchestrator returns `all_blocked=True` with
  reasons; UI shows the structured failure response (not a bad
  recommendation).
- *"7-day Hunza, July, family with kids 8 and 10"* → Safety Agent vetoes a
  Khunjerab-inclusive candidate; a different route wins; if Local Agent
  ranks the vetoed one first on cultural value, the dissent block fires.
- Latency: a debate finishes in roughly the time of the slowest single
  agent (parallel), not the sum of all 5. Test with `test_graph_parallel`.
- LLM call accounting: exactly **15 agent calls + 1 orchestrator call = 16
  calls** per fresh debate. Re-running same query = 0 calls.
- Local Experience Agent **never** mentions a place not in retrieved
  chunks. Verified via prompt design + a regression test that pre-warms an
  empty retrieval and asserts the resulting reasons say "no curated
  content".
- All Phase-3 tests green; coverage on `manzil/agents/` ≥ 75%.
- `replan()` invoked with a `road_closed` disruption on a sample query
  returns a `DebateResult` whose winner differs from the original (or
  `all_blocked=True` if no surviving route exists).

## Verification

```bash
# Build the RAG index (one-time per corpus change)
python scripts/build_rag_index.py

# Full agent + orchestrator test sweep
pytest tests/test_road_agent.py tests/test_safety_agent.py \
       tests/test_budget_agent.py tests/test_local_agent.py \
       tests/test_orchestrator_policy.py tests/test_all_blocked.py \
       tests/test_graph_parallel.py -v

# UI smoke
streamlit run ui/app.py
# Submit the all-blocked query above; observe failure response
# Submit the family/Khunjerab query; observe veto + dissent
# Submit normal query; check the scorecard expander shows structured args
```

## Risks & Plan B

| Risk | Likelihood | Plan B |
|---|---|---|
| **LangGraph parallel wiring takes a day** (the project's #2 critical-path risk per tech sketch §14) | Medium | Sequential execution. Debates are slower (5× a single call ≈ 30s) but the system works. |
| **RAG corpus quality is bad** after scrape (the project's #3 critical-path risk) | Medium | Hand-curate ~50 chunks across the most-visited destinations. Build the week-7 schedule with a 1-day buffer for this. |
| Hard-blocker thresholds are too strict (everything gets vetoed) | Medium | Tune the altitude-vs-group thresholds against the case base; require at least one surviving candidate in 90% of synthetic queries before declaring this acceptance criterion met. |
| `_llm_synthesize` exceeds Flash's 250 RPD on demo day | Low | Cache aggressively keyed on `(winner_id, scorecard_hash)`. Pre-warm in `seed_caches.py` (Phase 5). |
| Gemini SDK breaking change on `embedding-004` mid-phase | Low | RAG wrapper isolates the embedding call to one place; swap to OpenAI-style sentence-transformers locally if needed. |

## Owner split

| Track | Person 1 | Person 2 | Person 3 |
|---|---|---|---|
| Week 6 | review CBR weights against agent outputs | Road / Safety / Budget agents | UI shows structured arguments in expanders |
| Week 7 | (idle, prep Phase 5 eval design) | RAG wrapper + Local Agent | scrape + chunk corpus |
| Week 8 | review weights | Orchestrator + LangGraph parallel | end-to-end debate UI smoke |

## What this phase does **not** do

- Map widget, scorecard heatmap, debate trace animation (Phase 4)
- Side-by-side replanning UI (Phase 4)
- Memory/feedback loop (Phase 4)
- Offline ranking evaluation (Phase 5)
- Demo mode hardening (Phase 5)
- Final report (Phase 6)
