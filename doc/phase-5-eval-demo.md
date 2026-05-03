# Phase 5 — Evaluation & Demo Mode

> **Estimated:** Weeks 12–14.
> **Owner-lead:** Person 1 owns the offline RS evaluation; Person 3 owns
> demo-mode hardening and the RAG curation pass; Person 2 reviews
> scenario outcomes. Final report and submission are handled in
> [phase-6-report.md](phase-6-report.md).

## Goal

Two-track evaluation produces tables for the report. Demo mode is bulletproof.
The 12 scenario tests run in CI (or a make target). The final RAG curation
pass closes any gaps surfaced during real usage.

## Why this phase

A working demo is necessary but not sufficient. The grader needs evidence
that the system **generalizes** beyond the queries we hand-picked and that
it **doesn't crash** under edge cases. Without those, the project is a
tech demo, not a project.

This phase is also where we acknowledge limitations honestly — the
section-12 "Honest Acknowledgments" of the readme are converted into
measurable claims used in the Phase-6 report.

## Inputs / preconditions

- Phase 4 verified — full demo flow works
- Case base mature (~150 synthetic + however many feedback entries)
- All tests from prior phases passing

## Deliverables

### Two-track evaluation (Person 1 + Person 3)

The proposal commits to **two evaluation tracks** (PDF §7): offline ranking
metrics on the case base, and 12 hand-crafted scenario tests on the full
agent pipeline. We do not run a third user-satisfaction track — it was out
of scope per the proposal.

#### Track 1 — Offline RS metrics (Person 1)

| File | Responsibility |
|---|---|
| `eval/ranking_metrics.py` | Implement `precision_at_k`, `recall_at_k`, `ndcg_at_k`, and `mrr`. |
| `eval/run_recommender_eval.py` | 80/20 split on the case base. For each held-out case, run the recommender on the same `UserQuery` and check whether the actual chosen route appears in the top-5. |
| Configurations compared (PDF §7) | (a) **filter-only**, (b) **filter + content**, (c) **filter + CBR**, (d) **full hybrid** (filter + content + CBR with α=0.6 + MMR diversity). Each row of the output table is one configuration; columns are **P@5**, **R@5**, **NDCG@5**, **MRR**. |
| `eval/relaxation_eval.py` | Fixture of 20 deliberately over-constrained queries. Asserts: relaxation always fires, the surfaced relaxation note is non-empty, never returns more than 3 alternatives, and the result still respects the *hard* (non-soft) constraints. |

These eval scripts make **zero LLM calls** — they only exercise the
recommender. So they run cheaply and repeatedly during tuning.

#### Track 2 — Agent scenario tests (Person 1 + Person 2 + Person 3)

| File | Cases |
|---|---|
| `tests/test_scenarios.py` | 12 hand-crafted `UserQuery` inputs, each with asserted properties of the resulting `DebateResult`. Properties — not exact outputs — because the LLM's *judgment* is not unit-testable, but its structural behaviour is. |

The 12 scenarios:

| # | Scenario | Asserted property |
|---|---|---|
| 1 | Mid-budget Hunza in July, 4 friends | 3 candidates, all within budget+15%, scorecard fully populated |
| 2 | Karachi-to-Skardu road trip in January | `all_blocked=True`, every candidate has a Safety blocker |
| 3 | Family with kids 8/10, 7 days | No candidate exposes Khunjerab; safety reasons cite altitude |
| 4 | Wheelchair-accessible required | Every candidate avoids Fairy Meadows / Deosai |
| 5 | Foreign tourist (NOC required) → Khunjerab requested | Candidate is filtered or surfaced with NOC blocker |
| 6 | Over-constrained: 4 days Karachi-Skardu road | Relaxation fires; relaxation note non-empty |
| 7 | Adventure + cultural tags, ₨60k | At least one candidate scores ≥7 on Local Agent |
| 8 | Solo traveller, ₨40k, 5 days | All candidates flag solo-safety on the Safety Agent's reasons |
| 9 | Couple, photography style, October | Weather Agent's reasons for at least one candidate cite "clear autumn skies" |
| 10 | Mid-budget hybrid (fly + road) | At least one candidate uses `TravelMode.HYBRID` |
| 11 | Replan: original winner + landslide on day 3 | Replan returns a different `winner.candidate_id` |
| 12 | All-blocked → user shown structured failure | UI test (Selenium-free; render the page and assert the failure block is in the HTML) |

### Ethics measurements (Person 1)

The proposal (PDF §7) commits to measuring two ethical concerns beyond
the safety-veto mechanism that's already built into the Safety Agent:
synthetic-data bias and popularity bias. These are cheap to measure and
the numbers go straight into the Phase-6 report.

| File | Responsibility |
|---|---|
| `eval/ethics_eval.py` | (1) **Per-persona diversity:** for each of the 6 personas, run 25 sampled queries and report the standard deviation of the diversity-axis distribution across returned candidates. A persona that always gets the same axis profile is a red flag for synthetic-data bias. (2) **Recommendation frequency per destination:** count how often each destination appears in the winning candidate across the full eval sweep; report the Gini coefficient. A high Gini means the system over-recommends a few popular destinations. |
| `eval/results/ethics.txt` | Output of the above; goes into the Phase-6 report's "Honest Acknowledgments" section verbatim. |

These checks make zero LLM calls — they only exercise the recommender.

### Demo mode hardening (Person 3)

| File | Responsibility |
|---|---|
| `scripts/seed_caches.py` | Pre-warm `.manzil_cache/` for the 6-step demo flow + 2 backup queries. Walks through: form submission → debate → replan → feedback → second similar query. After running, the entire demo runs with `MANZIL_DEMO_MODE=1` and zero outbound calls. |
| `eval/demo_mode_check.py` | Asserts every cached call key in `seed_caches.py`'s expected list is present. Run once before demo day. |

### RAG corpus curation pass (Person 3)

| Action | Detail |
|---|---|
| Inspect `.manzil_cache/local_retrievals.json` | (Add this debug-cache during Phase 3.) For every retrieval that returned <3 chunks or low relevance scores, flag the destination + query. |
| Curate | Hand-write or hand-pick ~20 chunks for the gap destinations. Re-build the index. |
| Verify | The Local Agent's "no curated content" message should now be rare (under 5% of debates on the scenario suite). |

## Order of work

### Week 12 — Recommender eval (Person 1)

1. Day 1: `eval/ranking_metrics.py` (P@K, R@K, NDCG@K, MRR)
2. Day 2: `eval/run_recommender_eval.py`, 80/20 split harness
3. Day 3: Run all 4 configurations, produce the table
4. Day 4: `eval/relaxation_eval.py` + run on 20 over-constrained queries
5. Day 5: Tune `α` (hybrid mix) and `λ` (diversity) on the dev split;
   `eval/ethics_eval.py` (per-persona diversity + popularity Gini)

### Week 13 — Scenario tests + fuzz tests

1. Day 1–2: 12 scenario tests in `tests/test_scenarios.py`
2. Day 3: LLM output schema fuzz tests (replay deliberately malformed
   cached responses, verify retry-once-then-fallback)
3. Day 4–5: Iterate on any failing scenario; tune thresholds

### Week 14 — Curation + demo mode

1. Day 1–2: RAG corpus curation pass (Person 3)
2. Day 3: `scripts/seed_caches.py` walk-through
3. Day 4: `eval/demo_mode_check.py` + a clean-room demo-mode run
4. Day 5: Final eval results frozen; hand-off to Phase 6

## Acceptance criteria

- The full hybrid+diversity config (config d) beats the simpler configs
  on **at least two** of {P@5, R@5, NDCG@5, MRR}. Honest if it doesn't
  on the others — acknowledge in the Phase-6 report.
- Relaxation eval: 20/20 over-constrained queries return at least one
  candidate with a non-empty relaxation note.
- 12/12 scenario tests pass.
- Ethics eval produces `eval/results/ethics.txt`: per-persona diversity
  reported for all 6 personas, popularity Gini reported. (No threshold —
  these are honest-reporting numbers, not pass/fail.)
- `MANZIL_DEMO_MODE=1 streamlit run ui/app.py` runs the full 6-step demo
  flow with **zero** outbound network calls (verify by setting offline
  firewall rule or `iptables -A OUTPUT -p tcp --dport 443 -j DROP`).
- `eval/demo_mode_check.py` reports all expected cache keys present.

## Verification

```bash
# Track 1
python eval/run_recommender_eval.py --split 0.8 --seed 42 > eval/results/ranking.txt
python eval/relaxation_eval.py > eval/results/relaxation.txt
python eval/ethics_eval.py > eval/results/ethics.txt

# Track 2
pytest tests/test_scenarios.py -v
pytest tests/ -v --cov=manzil --cov-report=html  # full sweep

# Demo-mode rehearsal
python scripts/seed_caches.py
python eval/demo_mode_check.py
MANZIL_DEMO_MODE=1 streamlit run ui/app.py
# Walk the full demo with no internet, twice
```

## Risks & Plan B

| Risk | Likelihood | Plan B |
|---|---|---|
| Hybrid+diversity does *not* beat the simpler configs on the metrics | Medium | Honest reporting. The diversity selection trades raw ranking accuracy for argument quality — that's a feature, not a bug, and the report should articulate it. |
| Demo-mode walk-through reveals an un-seeded path | Medium | `eval/demo_mode_check.py` fails the build; iterate `seed_caches.py` until clean. |
| `gemini-2.5-flash[-lite]` deprecated mid-phase | Low | Update `Model` enum in `manzil/llm.py`; re-warm caches. |
| Scenario thresholds too strict; legitimate winners marked failures | Medium | Loosen the assertions to property-based forms (e.g., "at least one candidate" rather than "the winner") and document the relaxation in the report. |

## Owner split

| Track | Person 1 | Person 2 | Person 3 |
|---|---|---|---|
| Week 12 | recommender eval (full) | scenario test design review | RAG triage |
| Week 13 | scenario tests | LLM fuzz tests | scenario test UI smoke |
| Week 14 | (idle, prep Phase 6) | demo-mode check | RAG curation + cache seed |

## What this phase intentionally **leaves for the startup version**

These appear in the report's "Future work" section, not the project (PDF §5.2):

- Live road/weather/security feeds
- Booking integration (hotels, flights, transport)
- Mobile app
- Foreign-tourist mode + NOC application support
- Multi-language UI (Urdu, regional languages)
- User-tunable agent priority weights

Trying to do any of these in the project version produces something bad
at both. Acknowledge them, scope them out, move on.

## What this phase does **not** do

- Final report writing (Phase 6)
- Demo rehearsal #1 / #2 (Phase 6)
- Submission (Phase 6)
