# Phase 5 — Evaluation, Demo Mode, Polish

> **Estimated:** Weeks 12–16.
> **Owner-lead:** Person 1 owns the offline RS evaluation; Person 3 owns
> demo-mode hardening and the survey logistics; whole team owns the report.

## Goal

Three-track evaluation produces tables for the report. Demo mode is bulletproof.
The 12 scenario tests run in CI (or a make target). The user satisfaction
survey is run and analyzed. The final report is drafted, the presentation is
rehearsed, and the project is submitted.

## Why this phase

A working demo is necessary but not sufficient. The grader needs evidence
that the system **generalizes** beyond the queries we hand-picked, that it
**doesn't crash** under edge cases, and that **real users** found it useful.
Without those, the project is a tech demo, not a project.

This phase is also where we acknowledge limitations honestly — the section-12
"Honest Acknowledgments" of the readme are converted into measurable claims
in the report.

## Inputs / preconditions

- Phase 4 verified — full demo flow works
- Case base mature (~150 synthetic + however many feedback entries)
- All tests from prior phases passing

## Deliverables

### Three-track evaluation (Person 1 + Person 3)

#### Track 1 — Offline RS metrics (Person 1)

| File | Responsibility |
|---|---|
| `eval/ranking_metrics.py` | Implement `precision_at_k`, `recall_at_k`, `ndcg`. |
| `eval/run_recommender_eval.py` | 80/20 split on the case base. For each held-out case, run the recommender on the same `UserQuery` and check whether the actual chosen route appears in the top-3. |
| Configurations compared | (a) CBR-only, (b) content-only, (c) hybrid (`α=0.6`), (d) hybrid + diversity selection. Each row of the output table is one configuration; columns are P@1, P@3, R@3, NDCG@3. |
| `eval/relaxation_eval.py` | Fixture of 20 deliberately over-constrained queries. Asserts: relaxation always fires, the surfaced relaxation note is non-empty, never returns more than 3 alternatives, and the result still respects the *hard* (non-soft) constraints. |

These eval scripts make **zero LLM calls** — they only exercise the
recommender. So they run cheaply and repeatedly during tuning.

#### Track 2 — Agent scenario tests (Person 1 + Person 3)

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

#### Track 3 — User satisfaction survey (Person 1 + Person 3)

| Asset | Plan |
|---|---|
| `eval/survey/template.md` | A 5-minute Google Form. 10 classmates × 1 query each. Likert scales: clarity (1–5), perceived usefulness (1–5), trust in safety advice (1–5), would-use (yes/no), open-ended "what was missing." |
| `eval/survey/results.csv` | Anonymized responses. |
| `eval/survey/analysis.ipynb` | Bar charts + qualitative theme summary. Goes into the report as Section X.X. |

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

### Final report (Whole team)

| Section | Owner |
|---|---|
| Introduction + problem statement | Person 3 |
| Recommender architecture + offline metrics | Person 1 |
| Agent architecture + scenario tests | Person 2 |
| Memory loop + survey results | Person 1 + Person 3 |
| Honest acknowledgments | Whole team |
| Future work / startup case | Whole team |

The report draws **directly** from the readme's section 12 ("Honest
Acknowledgments") — synthetic data limits, RAG hallucination risk, mocked
live data, persona embed assumptions. We don't hide these; we measure
them where we can.

### Presentation rehearsal (Whole team, week 15–16)

- 8–10 minute live demo following the 6 steps from section 8 of the readme,
  always run with `MANZIL_DEMO_MODE=1`.
- Cover: problem → 3 candidates → debate animation → winner with scorecard
  + dissent → replan side-by-side → feedback loop → eval tables.
- Two backup queries pre-seeded in case the first one runs into something
  unexpected.

## Order of work

### Week 12 — Recommender eval (Person 1)

1. Day 1: `eval/ranking_metrics.py` (P@K, R@K, NDCG)
2. Day 2: `eval/run_recommender_eval.py`, 80/20 split harness
3. Day 3: Run all 4 configurations, produce the table
4. Day 4: `eval/relaxation_eval.py` + run on 20 over-constrained queries
5. Day 5: Tune `α` (hybrid mix) and `λ` (diversity) on the dev split

### Week 13 — Scenario tests + survey

1. Day 1–2: 12 scenario tests in `tests/test_scenarios.py`
2. Day 3: LLM output schema fuzz tests (replay deliberately malformed cached
   responses, verify retry-once-then-fallback)
3. Day 4: Survey design, push to classmates
4. Day 5: Collate first responses, iterate on the form if needed

### Week 14 — Curation + demo mode

1. Day 1–2: RAG corpus curation pass (Person 3)
2. Day 3: `scripts/seed_caches.py` walk-through
3. Day 4: `eval/demo_mode_check.py` + a clean-room demo-mode run
4. Day 5: Final survey results in; analysis notebook

### Week 15 — Report

1. Day 1–3: First draft, all sections
2. Day 4: Internal review, revise
3. Day 5: Demo rehearsal #1 (record it)

### Week 16 — Submission

1. Day 1: Final revisions on the report
2. Day 2: Demo rehearsal #2
3. Day 3: Submit. Defend.

## Acceptance criteria

- The hybrid+diversity config beats CBR-only and content-only on **at least
  two** of {P@1, P@3, NDCG@3}. Honest if it doesn't on the third —
  acknowledge in the report.
- Relaxation eval: 20/20 over-constrained queries return at least one
  candidate with a non-empty relaxation note.
- 12/12 scenario tests pass.
- Survey returns ≥10 valid responses; mean usefulness rating ≥3.5/5;
  qualitative themes summarized in 3–5 bullet points.
- `MANZIL_DEMO_MODE=1 streamlit run ui/app.py` runs the full 6-step demo
  flow with **zero** outbound network calls (verify by setting offline
  firewall rule or `iptables -A OUTPUT -p tcp --dport 443 -j DROP`).
- `eval/demo_mode_check.py` reports all expected cache keys present.
- Report draft ≥ 80% complete by end of week 15.

## Verification

```bash
# Track 1
python eval/run_recommender_eval.py --split 0.8 --seed 42 > eval/results/ranking.txt
python eval/relaxation_eval.py > eval/results/relaxation.txt

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
| Hybrid+diversity does *not* beat CBR-only on the metrics | Medium | Honest reporting. The diversity selection trades raw ranking accuracy for argument quality — that's a feature, not a bug, and the report should articulate it. |
| Survey participation < 10 | Medium | Lean on Person 3's classmates network; offer to help them with their projects in exchange. Report uses what we got. |
| Demo-mode walk-through reveals an un-seeded path | Medium | `eval/demo_mode_check.py` fails the build; iterate `seed_caches.py` until clean. |
| `gemini-2.5-flash[-lite]` deprecated mid-phase | Low | Update `Model` enum in `manzil/llm.py`; re-warm caches. |
| Last-week stress finds a real bug | High | Have a tight rollback path: every commit is on a branch, the demo-mode cache is committed to git so a working demo is always one `git checkout` away. |

## Owner split

| Track | Person 1 | Person 2 | Person 3 |
|---|---|---|---|
| Week 12 | recommender eval (full) | scenario test review | survey design + RAG triage |
| Week 13 | scenario tests | LLM fuzz tests | survey field + collate |
| Week 14 | survey analysis | demo-mode check | RAG curation + cache seed |
| Week 15 | report sections | report sections | report sections + rehearsal |
| Week 16 | revisions | revisions | revisions + final demo |

## What this phase intentionally **leaves for the startup version**

These appear in the report's "Future work" section, not the project:

- Real-time monitoring during the trip (push notifications, location-based alerts)
- Booking integration (hotels, flights, transport)
- Live road-condition feeds (NHA partnership)
- Live security advisories
- Foreign-tourist mode + NOC application support
- Mobile app
- Payment integration
- Multi-language UI (Urdu, regional languages)
- Group collaboration on a single trip
- User-tunable agent priority weights

Trying to do any of these in the project version produces something bad at
both. Acknowledge them, scope them out, move on.
