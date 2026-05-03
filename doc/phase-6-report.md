# Phase 6 — Final Report & Submission

> **Estimated:** Weeks 15–16.
> **Owner-lead:** Whole team. Person 3 coordinates submission logistics.

## Goal

Draft and submit the final IEEE-format report (≤6 pages, per PDF §8.3),
rehearse the live demo twice, and ship the project deliverables: public
GitHub repo, report PDF, eval results, and a recorded demo video as a
fallback.

## Why this phase

Phase 5 produced the evidence (eval tables, scenario test results,
demo-mode caches). This phase converts that evidence into the artifacts
the proposal committed to (PDF §8.3): the report, the demo, and the
GitHub repo. A working system that doesn't ship a clean report and a
clean demo loses points it should have kept.

## Inputs / preconditions

- Phase 5 verified — eval tables exist, demo mode runs offline
- All tests passing on a frozen branch from end-of-Phase-5
- Section-12 honest acknowledgments from the readme reviewed

## Deliverables

### Final report (Whole team)

| Section | Owner |
|---|---|
| Introduction + problem statement | Person 3 |
| Recommender architecture + offline metrics (Track 1) | Person 1 |
| Agent architecture + scenario tests (Track 2) | Person 2 |
| Memory loop + replanning case study | Person 1 + Person 3 |
| Honest acknowledgments | Whole team |
| Future work / startup case | Whole team |

The report:

- ≤ 6 pages, IEEE format (per PDF §8.3)
- Draws **directly** from the readme's section 12 ("Honest Acknowledgments")
  — synthetic data limits, RAG hallucination risk, mocked live data,
  persona embed assumptions. We don't hide these; we measure them where
  we can.
- Tables are generated from `eval/results/*.txt` so claims are traceable
  to the run that produced them.

### Presentation rehearsal (Whole team)

- 8–10 minute live demo following the 6 steps from section 8 of the
  readme, always run with `MANZIL_DEMO_MODE=1`.
- Per PDF §8.3, the demo must cover: a typical query, an over-constrained
  query (showing the relaxation banner), the disruption-replan, and the
  memory loop.
- Concretely: problem → 3 candidates → debate animation → winner with
  scorecard + dissent → over-constrained query (relaxation fires) →
  replan side-by-side → feedback loop → eval tables.
- Two backup queries pre-seeded in case the first one runs into something
  unexpected.
- Recorded as a 5-minute screencast as a fallback if the live demo fails
  on the day.

### Submission package (per PDF §8.3)

| Artifact | Detail |
|---|---|
| Public GitHub repo | All source, README updated with quickstart, MIT license. |
| Final report PDF | IEEE format, ≤ 6 pages, committed to the repo at `report/manzil_report.pdf`. |
| `eval/results/` | `ranking.txt`, `relaxation.txt`, scenario results. |
| Recorded demo video | 5 minutes, mp4 or unlisted YouTube, linked from the README. |

## Order of work

### Week 15 — Report draft

1. Day 1–3: First draft, all sections
2. Day 4: Internal review, revise
3. Day 5: Demo rehearsal #1 (record it, watch it back)

### Week 16 — Submission

1. Day 1: Final revisions on the report
2. Day 2: Demo rehearsal #2; record the backup screencast
3. Day 3: Submit the GitHub repo + report; defend.

## Acceptance criteria

- Report draft ≥ 80% complete by end of week 15.
- Final report ≤ 6 pages, IEEE format.
- Demo rehearsal #2 runs cleanly end-to-end with `MANZIL_DEMO_MODE=1`
  and zero outbound calls.
- All eval tables and scenario results referenced in the report match
  the files in `eval/results/`.
- GitHub repo public; the README quickstart works on a fresh clone.
- Backup screencast recorded and linked from the README.

## Verification

```bash
# Demo dry-run (no internet)
MANZIL_DEMO_MODE=1 streamlit run ui/app.py
# Walk the 6-step flow, time it, confirm < 10 minutes

# Full test sweep one more time
pytest tests/ -v --cov=manzil

# Confirm eval results are still reproducible
python eval/run_recommender_eval.py --split 0.8 --seed 42

# Sanity-check report length (rough word count)
wc -w report/manzil_report.tex
```

## Risks & Plan B

| Risk | Likelihood | Plan B |
|---|---|---|
| Last-week stress finds a real bug | High | Tight rollback path: every commit is on a branch, the demo-mode cache is committed to git so a working demo is always one `git checkout` away. |
| Live demo fails on the day | Medium | Switch to the backup screencast; the rehearsal recording counts as a working demonstration. |
| Report exceeds 6 pages | Medium | Cut the related-work section to one paragraph; move detailed tables to an appendix; trim the acknowledgments. |
| `gemini-2.5-flash[-lite]` deprecated mid-phase | Low | Update `Model` enum in `manzil/llm.py`; re-warm caches. |

## Owner split

| Track | Person 1 | Person 2 | Person 3 |
|---|---|---|---|
| Week 15 | RS sections + offline metrics tables | Agent + scenario sections | Intro + UI walkthrough + memory section + rehearsal #1 |
| Week 16 | revisions | revisions | revisions + final demo + backup screencast + submit |

## What this phase does **not** do

- Any new feature work — Phase 5 is the freeze
- Reruns of the offline eval beyond reproducibility checks
- Live deployment / hosting beyond the GitHub repo
