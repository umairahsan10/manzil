# Phase 2 — Real Recommender

> **Estimated:** Weeks 4–5.
> **Owner-lead:** Person 1 (RS Lead). Person 3 wires UI; Person 2 reviews
> the contract surface.

## Goal

Replace the Phase-1 stub recommender with the full pipeline:

> constraint filter → route enumeration → CBR scoring → content scoring →
> hybrid scoring → constraint relaxation (if needed) → MMR diversity selection

The three candidates returned are **genuinely diverse** along the section-4
axes (scope / mode-mix / pace / risk / budget posture) — not three
near-duplicates of the same trip.

## Why this phase

This is the layer that separates Manzil from a search box. A bad
recommender produces three look-alike candidates, and the downstream debate
becomes meaningless. A good one frames the agents' debate around real
trade-offs.

It also implements **constraint relaxation**, the most distinctive
behaviour of the recommender: when no feasible route exists, we don't fail
silently — we relax the soft constraints in priority order and tell the
user what we relaxed.

## Inputs / preconditions

- Phase 1 verified — UI runs end-to-end, stub recommender returns 3 cards
- Schemas frozen
- WeatherAgent emitting real arguments

## Deliverables

### Data expansion (Person 1)

| File | Change |
|---|---|
| `data/destinations.json` | Expand from 5 → 10–15 entries. Add: `khaplu`, `deosai`, `swat-kalam`, `shogran`, `neelum`, `gilgit`, `passu`, `attabad`, `chitral`. |
| `data/personas.json` | 6 persona definitions. Each persona has a name, a preference distribution over `style_tags`, a `difficulty_tolerance` mean, a `budget_pkr` band, and a `group_composition` weight. |
| `data/case_base.json` | Output of `scripts/generate_case_base.py`. ~150 entries. Committed to repo. |

### Persona-grounded synthetic generator (Person 1)

| File | Responsibility |
|---|---|
| `scripts/generate_case_base.py` | For each persona, draw ~25 `UserQuery` objects from the persona's distribution (with controlled noise). For each, sample a `chosen_route` from the destinations that match the persona's preferences, assign a `rating` that's a noisy function of `(preference, destination match)`. Output `data/case_base.json` with 150 `CaseBaseEntry` objects (`is_synthetic=True`). Deterministic via `--seed`. |

### Recommender modules (Person 1)

| File | Responsibility |
|---|---|
| `manzil/recommender/filter.py` | `filter_destinations(query, destinations) -> List[Destination]`. Drops any destination whose `season_open[query.travel_month-1] is False`, fails NOC, fails accessibility, or fails group-fit. Returns reasoning per dropped destination for the relaxation layer. |
| `manzil/recommender/enumerate.py` | `enumerate_routes(destinations, query) -> List[List[str]]`. Builds candidate destination sequences. Cap: max 4 destinations, max 20 sequences total via heuristic pruning (drive-time, region clustering). |
| `manzil/recommender/cbr.py` | `score_route(route, query, case_base, k=10) -> float`. Weighted similarity over `query` attributes (group_size, budget, days, month, mode, style, difficulty), where weights are tuned on a held-out split during evaluation. Score = rating-weighted average of cases that visited a similar destination set. |
| `manzil/recommender/content.py` | `score_route(route, query, destinations) -> float`. Cosine similarity between user `style_tags`/`difficulty_tolerance` vector and an aggregate `activity_tags`/`difficulty` vector for the route. |
| `manzil/recommender/hybrid.py` | `s = α · cbr + (1-α) · content`, default `α=0.6`. |
| `manzil/recommender/relaxation.py` | `relax(query) -> Iterator[Tuple[query_modified, relaxation_note]]`. Priority order: budget +15%, days −1, preferred-destinations soft. Yields up to 3 relaxations. |
| `manzil/recommender/diversity.py` | `pick_diverse_three(scored_routes, λ=0.5) -> List[RouteCandidate]`. Greedy MMR: pick top-1; iteratively pick 2 more maximizing `(score − λ · max_axis_similarity_to_already_picked)`. Similarity is over the 5 diversity axes. Tags each picked candidate with the axes it represents. |
| `manzil/recommender/pipeline.py` | **Replaces** the Phase-1 stub. Orchestrates: filter → enumerate → CBR → content → hybrid → diversity. If filter or enumerate yields empty, run `relaxation.relax(query)` and retry up to 3 times; surface the relaxation notes on the returned candidates. |

### UI updates (Person 3)

| File | Change |
|---|---|
| `ui/pages/plan.py` | Each candidate card now shows its diversity-axis tags ("scope: multi-region", "pace: relaxed"). If any relaxation fired, render a banner above the cards: *"No routes matched your exact constraints. Showing options if you increase your budget by 12% / drop a day / loosen your destination preferences."* |

### Tests (Person 1)

| File | Cases |
|---|---|
| `tests/test_filter.py` | Season closed → filtered. NOC zone + foreigner → filtered. Wheelchair constraint → filtered if not accessible. Group composition mismatch → filtered. |
| `tests/test_cbr.py` | Identical case → similarity 1.0. Far cases → near-zero. Returned score is rating-weighted, not just nearest-neighbour rating. |
| `tests/test_content.py` | High-overlap style tags → high score. Disjoint tags → low. |
| `tests/test_diversity.py` | Three near-identical scored routes → MMR returns 3 *different* picks (proves λ does its job). High-λ regime favours diversity over score. |
| `tests/test_relaxation.py` | Over-constrained query → relaxation fires; `relaxation_note` is non-empty on returned candidates; never returns more than 3 relaxations. |
| `tests/test_pipeline_smoke.py` | Updated to assert the 3 candidates have *different* `diversity_axes` tags. |

## Order of work

1. **Day 1–2:** Person 1 expands `destinations.json`, defines `personas.json`,
   writes `scripts/generate_case_base.py`, generates the case base.
2. **Day 3:** `filter.py` + `enumerate.py` + tests. Manual sanity-check on a
   handful of queries.
3. **Day 4:** `cbr.py` + tests. **Critical-path risk** — if neighbours look
   wrong, fix the similarity weights now before more layers depend on it.
4. **Day 5:** `content.py` + `hybrid.py` + tests.
5. **Day 6:** `relaxation.py` + tests.
6. **Day 7:** `diversity.py` + tests. This is where the demo gets visibly
   better — three meaningfully different candidates.
7. **Day 8:** Wire `pipeline.py`, replace Phase-1 stub, update UI banner +
   axis tags. End of week 5 = **Mid-1 milestone**.

## Acceptance criteria

- For *"7-day Hunza, July, ₨120k, road, 4 friends, adventure+cultural"*
  the 3 returned candidates differ on **at least 2** diversity axes.
- For *"4-day Karachi-to-Skardu road in January"* the relaxation banner
  fires, and at least one candidate is returned (e.g., the days-relaxed
  variant).
- CBR module's nearest-neighbour output passes a manual sanity check on 3
  hand-picked queries (Person 1 reviews and signs off).
- `pytest tests/test_filter.py tests/test_cbr.py tests/test_content.py
  tests/test_diversity.py tests/test_relaxation.py` all green.
- Coverage on `manzil/recommender/` ≥ 80%.

## Verification

```bash
# Generate the case base
python scripts/generate_case_base.py --seed 42

# Run all recommender tests
pytest tests/ -v -k "filter or cbr or content or diversity or relaxation or pipeline"

# Coverage
pytest tests/ --cov=manzil/recommender --cov-report=term-missing

# UI smoke
streamlit run ui/app.py
# Submit an over-constrained query; observe relaxation banner
# Submit a normal query; observe diversity-axis tags on each card
```

## Risks & Plan B

| Risk | Likelihood | Plan B |
|---|---|---|
| **CBR similarity function produces nonsensical neighbours** (the project's #1 critical-path risk per tech sketch §14) | Medium | Fall back to content-only scoring with a richer feature space (add destination embeddings via Gemini's free embedding endpoint). Document the fallback in the report. |
| Diversity MMR picks dominated by a single axis | Medium | Hand-tune the per-axis similarity weights; add a unit test that asserts at least 2 axes vary across the 3 picks. |
| Case base too small for stable nearest-neighbour | Low | Bump generator to 250 cases (5 personas × 50). Synthetic data is cheap. |
| Relaxation fires too aggressively (every query gets relaxed) | Low | Tighten the budget +15% threshold to +10%; add a "show me the un-relaxed result" mode in the UI. |

## Owner split

| Track | Person 1 | Person 2 | Person 3 |
|---|---|---|---|
| Days 1–2 | data + case base | (Phase 3 prep: read RAG docs) | UI mockup for axis tags |
| Days 3–7 | filter / enumerate / CBR / content / hybrid / relax / diversity | review CBR weights | (continues UI work) |
| Day 8 | wire pipeline | review final contract | banner + axis tags wired |

## What this phase does **not** do

- Real Road / Safety / Budget / Local agents (still stubs from Phase 1)
- Orchestrator improvements (still the minimal Phase-1 version)
- Map widget, scorecard heatmap (Phase 4)
- Replanning under disruption (Phase 4)
- Memory loop (Phase 4)
- Evaluation tables (Phase 5)
