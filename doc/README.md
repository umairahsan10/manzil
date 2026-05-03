# Manzil — Phased Build Documentation

This folder is the working reference for building Manzil. The two top-level
design docs ([../Readme.md](../Readme.md) and
[../Manzil_Tech_Sketch.md](../Manzil_Tech_Sketch.md)) describe **what** the
system is and **how** it should be architected. The files in this folder
describe **the order in which we actually build it** — six self-contained
phases, each ending in a runnable, demoable system.

## Why phases at all

The 16-week schedule in section 14 of the tech sketch is correct but reads as
one long checklist. A phased structure groups that checklist into logical
slices where each slice:

- Replaces a stub with a real implementation rather than building one whole
  layer in isolation
- Leaves the system runnable end-to-end (`streamlit run ui/app.py` always
  works)
- Has explicit acceptance criteria so we know when to move on
- Has a named owner from the 3-person team split

We do **not** start a phase until the previous phase's verification passes.
That rule is what keeps it clean and smooth.

## Phase index

| # | Phase | Weeks | Owner-lead | Doc |
|---|---|---|---|---|
| 0 | Foundations & Spine | 1 | Whole team | [phase-0-foundations.md](phase-0-foundations.md) |
| 1 | Thin Vertical Slice | 2–3 | Person 3 (Integration) | [phase-1-thin-slice.md](phase-1-thin-slice.md) |
| 2 | Real Recommender | 4–5 | Person 1 (RS Lead) | [phase-2-recommender.md](phase-2-recommender.md) |
| 3 | Full Agent Cast + Orchestrator + Replanning | 6–8 | Person 2 (Agent Lead) | [phase-3-agents-orchestrator.md](phase-3-agents-orchestrator.md) |
| 4 | UI Polish + Memory Loop | 9–11 | Person 3 | [phase-4-ui-replanning-memory.md](phase-4-ui-replanning-memory.md) |
| 5 | Evaluation & Demo Mode | 12–14 | Person 1 + Person 3 | [phase-5-eval-demo.md](phase-5-eval-demo.md) |
| 6 | Final Report & Submission | 15–16 | Whole team | [phase-6-report.md](phase-6-report.md) |

> Aligned with the project proposal (PDF §6). The PDF lays out 7 calendar
> phases over 15 days; we keep the same scope but split implementation into
> 7 doc-phases (0–6) over a longer course-pace timeline so each one ends
> in a runnable system. Phase 0 (Foundations) and Phase 1 (Thin Slice)
> are doc-only — the PDF subsumes them under "Setup & Data Collection".

## Team roles (carry through every phase)

- **Person 1 — Recommender Lead.** Owns `manzil/recommender/`,
  `scripts/generate_case_base.py`, `eval/`. Drives weeks 3–5 and 12–13.
- **Person 2 — Agent Lead.** Owns `manzil/agents/`, `manzil/graph/`,
  `manzil/tools/rag.py`. Drives weeks 6–8 and 10.
- **Person 3 — Integration & UI.** Owns `ui/`, knowledge-base curation,
  `manzil/tools/weather_api.py`, `data/local_corpus/`, demo mode. Drives
  weeks 1–2, 9–11, 14.

## Cross-cutting engineering rules (apply to every phase)

These are not negotiable and we do not make exceptions:

1. **The LLM is called once per agent per candidate**, after deterministic
   analysis. 5 agents × 3 candidates × 1 call + 1 Orchestrator call = 16 calls
   per debate. Anything that pushes us above this is a bug.
2. **Caching is mandatory from day 1.** Cache by `(model, prompt, temperature)`
   for raw LLM calls and `(agent_name, candidate_route_hash)` for agent
   arguments. Re-running the same debate during dev hits the API zero times.
3. **Every LLM response is Pydantic-validated.** Retry-once with a stricter
   prompt; on a second failure, fall back to a deterministic
   `AgentArgument(confidence=0.0)`. The system never crashes mid-debate.
4. **Layer boundaries:** nothing in `manzil/` imports from `ui/` or `scripts/`;
   nothing in `ui/` or `scripts/` imports from `tests/`.
5. **Demo mode (`MANZIL_DEMO_MODE=1`) refuses outbound calls.** Demo day
   always runs with this flag.
6. **Pydantic v2 syntax.** `.model_dump()` not `.dict()`,
   `.model_validate()` not `.parse_obj()`, `field_validator` not `validator`.

## Reading the phase docs

Each phase doc has the same structure:

- **Goal** — one sentence
- **Why this phase** — what it unlocks
- **Inputs / preconditions** — what must already exist
- **Deliverables** — file-by-file with responsibilities
- **Order of work** — the sequence inside the phase
- **Acceptance criteria** — how we know we're done
- **Verification** — exact commands to run
- **Risks & Plan B** — what could go wrong and the fallback
- **Owner split** — who does what when the team is parallelizing

When in doubt, the [tech sketch](../Manzil_Tech_Sketch.md) is the source of
truth on architecture; the [Readme](../Readme.md) is the source of truth on
product behavior; and the phase docs here are the source of truth on
**execution order**.
