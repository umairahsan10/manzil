# Phase 1 — Thin Vertical Slice

> **Estimated:** Weeks 2–3.
> **Owner-lead:** Person 3 (Integration / UI), with support from Person 1
> (data files + stub recommender) and Person 2 (`BaseAgent` + WeatherAgent).

## Goal

Form → 3 candidates → "winner" page works end-to-end with a **stub
recommender** and **one real agent** (Weather). Proves the full pipeline
shape before any layer is fully built.

## Why this phase

A normal "build one layer at a time" approach hides integration issues until
late. By making the spine work end-to-end with stubs first, we surface
contract bugs *now*, when they're cheap to fix. By the end of this phase
**the demo flow exists**; every later phase swaps a stub for a real
implementation behind the same contract.

## Inputs / preconditions

- Phase 0 complete and verified
- Three healthchecks green
- `pytest tests/` clean

## Deliverables

### Data (Person 1)

| File | Contents |
|---|---|
| `data/destinations.json` | 5 destinations: `hunza-karimabad`, `skardu`, `naran`, `fairy-meadows`, `murree`. Every field in the `Destination` schema populated with real numbers. Real altitudes, real coords, plausible `cost_per_day` tiers. |
| `data/costs.json` | Skeletal cost table: per region, per season (`high`/`shoulder`/`low`), per quality tier. Transport rows for the relevant origin→destination pairs. |
| `data/road_knowledge.json` | The major passes (`khunjerab`, `babusar`, `lowari`, `deosai`) with `open_months`. Drive-time matrix between the 5 destinations. |
| `data/safety_knowledge.json` | Per-destination altitude, NOC requirement, nearest hospital/police lookup. Altitude-vs-group thresholds. |

These files are *minimum viable* — Phase 2 expands `destinations.json` to
10–15 entries.

### Recommender (stub) (Person 1)

| File | Responsibility |
|---|---|
| `manzil/recommender/pipeline.py` | One public function `recommend(query: UserQuery) -> List[RouteCandidate]`. Returns 3 hand-crafted candidates regardless of input. The 3 should differ along the diversity axes (a "safe default", a "value pick", an "ambitious option") so the downstream debate has something real to argue between. |

### Agents (Person 2)

| File | Responsibility |
|---|---|
| `manzil/agents/base.py` | `BaseAgent(ABC)` with the section-6 contract: `evaluate(candidate, query) -> AgentArgument` orchestrates `_analyze` (deterministic), `_check_blocker`, `_score`, `_llm_argue`. `_llm_argue` is shared, calls `llm.complete_json(...)` against the `LLMArgumentPayload` schema. |
| `manzil/agents/weather.py` | First **real** agent. `_analyze` calls Open-Meteo per destination per candidate; `_score` translates precip/temp into 0–10; `_check_blocker` returns a blocker if all-day rain or hostile temps; `_llm_argue` produces the natural-language reasons/concerns. |
| `manzil/agents/road.py` | **Stub.** Returns a canned `AgentArgument` with `score=7.0`, no LLM call. Will become real in Phase 3. |
| `manzil/agents/safety.py` | **Stub.** Same shape, deterministic score from altitude lookup only. |
| `manzil/agents/budget.py` | **Stub.** Compares `candidate.estimated_cost` to `query.budget_pkr`, scores linearly. |
| `manzil/agents/local.py` | **Stub.** Returns a fixed reasons list. |
| `manzil/agents/orchestrator.py` | Minimal: weighted-aggregate score (using the Phase-3 weights so the contract is set), no dissent detection, no why-not, no LLM call. Returns a `DebateResult` with `winner` + `scorecard` + empty `dissenting_opinion` / `why_not`. |

### Graph (Person 2)

| File | Responsibility |
|---|---|
| `manzil/graph/debate_graph.py` | LangGraph `StateGraph` over `DebateState`. **Sequential** in this phase (parallel comes in Phase 3). `fan_out → weather → road → safety → budget → local → collect → orchestrator → END`. |

### UI (Person 3)

| File | Responsibility |
|---|---|
| `ui/pages/plan.py` | The form (group/days/budget/month/mode/origin/style/difficulty), submit button, 3-candidate preview cards (id, label, cost, days), debate runs in-line, winner section shows the day-by-day scaffold + the raw scorecard JSON in an expander. |
| `ui/app.py` | Add page navigation (Plan / Healthcheck) using `st.sidebar.radio` or `st.navigation`. |

### Tests

| File | Cases |
|---|---|
| `tests/test_pipeline_smoke.py` | A canonical `UserQuery` runs end-to-end and returns a `DebateResult` with a non-null winner. |
| `tests/test_base_agent.py` | A fake agent subclass produces a valid `AgentArgument`. `_llm_argue` is mocked to return a `LLMArgumentPayload`. |

## Order of work

1. **Day 1:** Person 1 lands the 4 JSON data files; Person 2 lands
   `BaseAgent` skeleton + the four stub agents; Person 3 sketches the form.
2. **Day 2:** Person 2 writes WeatherAgent fully (deterministic analysis +
   real `_llm_argue` call); Person 1 writes the stub `recommend()`.
3. **Day 3:** Person 2 writes the LangGraph wiring + minimal Orchestrator;
   Person 3 wires the UI to call `recommend()` then run the graph then render
   the result.
4. **Day 4:** Smoke test, fix integration bugs, commit, demo to ourselves.

## Acceptance criteria

- Submitting a query for *"7-day Hunza trip in July, 4 friends, ₨120k,
  road"* shows 3 distinct candidate cards within 3 seconds.
- Clicking through, the debate completes within ~10 seconds (first run with
  cold cache; subsequent runs are sub-second).
- Exactly **6 LLM calls** happen on the first run (1 per candidate from
  WeatherAgent + 3 stubbed-out for Orchestrator-text — actually the
  Orchestrator is text-free in this phase, so **3 LLM calls total**).
- A second submission of the same query makes **zero** LLM calls.
- The winner section shows a populated scorecard (5 agents × 3 candidates =
  15 cells, all non-null).
- `pytest tests/` still passes.

## Verification

```bash
streamlit run ui/app.py
# 1. Submit query above; observe 3 candidate cards
# 2. Wait for debate; observe winner + scorecard
# 3. Re-submit same query; observe sub-second response (cache replay)
# 4. tail -f .manzil_cache/llm.json -- should grow on first run, not on second

pytest tests/ -v
```

## Risks & Plan B

| Risk | Likelihood | Plan B |
|---|---|---|
| LangGraph wiring takes longer than expected | Medium | Skip LangGraph for Phase 1 — write a 30-line `for agent in agents: agent.evaluate(c)` loop. Wire LangGraph in Phase 3 when parallelism actually matters. |
| Open-Meteo response is too sparse for some Pakistan coords (high altitude noise) | Low | Fall back to a synthetic seasonal pattern from `road_knowledge.json` for any destination where the API returns insufficient data. |
| Pydantic v2 enum serialization quirks (`Enum` → string in JSON) | Low | Use `model_dump(mode="json")` in `cache.set` calls; we already do this in `weather_api.py`. |

## Owner split

| Track | Person 1 | Person 2 | Person 3 |
|---|---|---|---|
| Day 1 | data JSON | `BaseAgent`, stub agents | UI form sketch |
| Day 2 | stub `recommend()` | WeatherAgent (real) | candidate-preview cards |
| Day 3 | review stub diversity | LangGraph + Orchestrator | end-to-end wiring |
| Day 4 | smoke fixes | smoke fixes | smoke fixes + demo |

## What this phase does **not** do (deferred)

- Real recommender (Phase 2)
- Road / Safety / Budget / Local agents real (Phase 3)
- Orchestrator dissent detection, why-not, LLM synthesis (Phase 3)
- LangGraph parallel fan-out (Phase 3)
- Map widget, scorecard heatmap, debate trace animation (Phase 4)
- Replanning (Phase 3), feedback loop (Phase 4)
- Evaluation, demo mode hardening (Phase 5)

If anyone is tempted to pull these forward, the answer is **no**. The point
of the thin slice is the slice, not the depth.
