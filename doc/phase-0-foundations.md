# Phase 0 — Foundations & Spine

> **Status:** code complete; awaiting runtime verification by user.
> **Estimated:** Week 1.
> **Owner-lead:** Whole team in parallel.

## Goal

Take an empty repo to a bootable Streamlit app with Gemini and Open-Meteo
proven to work, all data contracts (Pydantic schemas) frozen, and a strict
cache layer wired in from the start so day-to-day development burns zero
quota.

## Why this phase

Every later phase depends on (a) the schemas being right and (b) every
expensive call being cached. If we get either of these wrong now, every
subsequent phase pays a tax. Spending a week here is the cheapest insurance
the project will buy.

## Inputs / preconditions

- Python 3.11+ installed (we developed against 3.12.11)
- A Gemini API key from <https://aistudio.google.com/app/apikey> (free tier)
- Working internet for the first run (subsequent runs are cache-served)

## Deliverables (file-by-file)

| File | Responsibility |
|---|---|
| [../.gitignore](../.gitignore) | Excludes venv, `.env`, caches (`.manzil_cache/`, `chroma_db/`), pyc, OS noise. |
| [../requirements.txt](../requirements.txt) | Pinned versions for every Phase 0–2 runtime dep. **`chromadb` is commented out** and deferred to Phase 3 — its build pulls `cmake` which on some Windows/msys2 Python builds fails an SSL cert verify during a bootstrap download. We install it fresh when Phase 3 actually needs it. |
| [../.env.example](../.env.example) | Template for `GEMINI_API_KEY`, `MANZIL_USE_CACHE`, `MANZIL_DEMO_MODE`, `MANZIL_CACHE_DIR`. |
| `manzil/__init__.py` | Package marker, exposes `__version__`. |
| `manzil/{recommender,agents,tools,graph,memory}/__init__.py` | Sub-package markers. |
| [../manzil/schemas.py](../manzil/schemas.py) | **The contracts.** `TravelMode`, `GroupType`, `Destination`, `UserQuery`, `RouteCandidate`, `AgentArgument`, `DayStop`/`DayPlan`/`DayByDayPlan`, `DebateResult`, `CaseBaseEntry`, `WeatherData`, `CostBreakdown`, `LLMArgumentPayload`. Pydantic v2 throughout. |
| [../manzil/tools/cache.py](../manzil/tools/cache.py) | File-backed JSON cache, namespace-keyed (`llm.json`, `weather.json`, …). `get` / `set` / `clear` / `stable_key` / `is_demo_mode` / `is_enabled`. Demo-mode misses raise `CacheMiss`. |
| [../manzil/llm.py](../manzil/llm.py) | Gemini wrapper. Two-tier model enum (`Model.FLASH_LITE`, `Model.FLASH`). `complete()` returns text; `complete_json(schema)` parses + retries once + raises `LLMParseError`. `healthcheck()` for the UI. Lazy client init so demo mode doesn't need the API key. |
| [../manzil/tools/weather_api.py](../manzil/tools/weather_api.py) | Open-Meteo `forecast` wrapper. Cached by `(lat, lon, start_date, days)`. Returns a `WeatherData`. `healthcheck()` calls Karimabad coords for the UI. |
| [../ui/app.py](../ui/app.py) | Streamlit entrypoint. Env metric row + 3 healthcheck columns (schemas / Gemini / Open-Meteo). |
| [../tests/test_llm_cache.py](../tests/test_llm_cache.py) | Pytest cases: `stable_key` order-insensitivity, get/set round-trip, demo-mode miss raises, demo-mode hit serves, `llm.complete()` never imports `google.generativeai` when warm. |

## Order of work

This is the only phase where everyone can work fully in parallel because the
schema is the contract that unblocks everyone else. Recommended one-day flow:

1. Person 3 (15 min): `git init`, write `.gitignore`, `requirements.txt`,
   `.env.example`, create the directory skeleton.
2. Whole team (60 min, together): write `manzil/schemas.py`. Argue field by
   field. This is the single most consequential file in the project.
3. Person 2 (90 min): `manzil/tools/cache.py` + `tests/test_llm_cache.py`.
4. Person 2 (60 min): `manzil/llm.py`. Lazy import — do not require the API
   key at module import time, only at first live call.
5. Person 3 (45 min): `manzil/tools/weather_api.py`.
6. Person 3 (30 min): `ui/app.py` healthcheck page.
7. Whole team (15 min): run the verification steps below.

## Acceptance criteria

All of the following must be true before we move to Phase 1:

- [x] `python -m compileall manzil ui tests` exits 0 (already verified)
- [ ] `pip install -r requirements.txt` succeeds in a fresh venv
- [ ] `pytest tests/` is all green (8 tests in `test_llm_cache.py`)
- [ ] `streamlit run ui/app.py` shows three green healthchecks
- [ ] **Refreshing** the Streamlit page returns instantly — Gemini call is
      replayed from `.manzil_cache/llm.json`, no second API call
- [ ] `MANZIL_DEMO_MODE=1 streamlit run ui/app.py` works using only the
      cache (proves the demo-day flag works)

## Verification (exact commands)

```bash
# from project root
python -m venv .venv
source .venv/Scripts/activate          # Git Bash on Windows
# or:  .venv\Scripts\activate          # cmd.exe
pip install -r requirements.txt

cp .env.example .env
# edit .env, paste GEMINI_API_KEY=...

pytest tests/ -v                       # expect 8 passed
streamlit run ui/app.py                # 3 green ticks

# Demo-mode replay test (only after a successful first run):
MANZIL_DEMO_MODE=1 streamlit run ui/app.py
```

## Risks & Plan B

| Risk | Likelihood | Plan B |
|---|---|---|
| Gemini model IDs differ from `gemini-2.5-flash[-lite]` | Medium | Swap the `Model` enum values in [../manzil/llm.py](../manzil/llm.py); cache layer is model-agnostic. |
| ~~`chromadb` install is heavy / fails on Windows~~ — **realized** in this build; resolved by deferral | — | Already commented out in `requirements.txt`; we add it back at the start of Phase 3 (alongside the RAG corpus work). If the SSL error reproduces then, install pre-built CMake separately so chromadb's build doesn't need to bootstrap-download it. |
| `google-generativeai` SDK has had breaking renames | Low | Wrap the SDK call in `manzil/llm.py:_ensure_client()`; if rename, fix in one place. |

## Owner split

This phase is the only one where pure parallel work makes sense — there is no
serial dependency once the schemas are written. After Phase 0 the work
funnels through one lead per phase.

## Substitutions flagged (vs. tech sketch)

- **Pydantic v2 (not v1).** The tech sketch's snippet `raw_data: Dict` was
  taken as Pydantic-v1 style; we use v2 (`model_dump()`, `field_validator`).
  Every model has `model_config = ConfigDict(extra="forbid")` so unknown
  fields are caught at boundary time.
- **`httpx` instead of `requests`** for the Open-Meteo wrapper. Same
  surface area, better timeouts story, async-ready if we ever need it.
