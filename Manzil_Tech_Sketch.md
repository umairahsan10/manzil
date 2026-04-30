# Manzil — Technical Implementation Sketch

*Companion to the problem-solution document. This is the "how we actually build it" doc, scoped for a 3-person team at 6-8 hrs/week each over 16 weeks, on the Gemini free tier.*

---

## 1. Tech Stack and Rationale

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Standard for ML/agent work; everyone on the team knows it |
| Agent framework | LangGraph | State-machine model is explicit, debuggable, and the graph itself becomes a diagram for the report |
| LLM provider | Gemini API (free tier) | Free, generous limits (1,000 RPD on Flash-Lite), no credit card |
| LLM models | Gemini 2.5 Flash-Lite (agents), Flash (Orchestrator) | Flash-Lite for high-throughput agent argument generation; Flash for the Orchestrator's deeper synthesis |
| Vector store (RAG) | ChromaDB (local, file-backed) | No infra setup, persists between runs, free |
| Embedding model | Gemini text-embedding-004 (free tier) | Same provider, no extra dependency |
| Storage | JSON / CSV files | The data is small; a relational DB is overkill |
| UI | Streamlit | Fastest path to a working demo; map widgets via Folium/Pydeck |
| External APIs | Open-Meteo (weather, free, no key) | No registration, generous rate limits, structured forecast data |
| Maps | OpenStreetMap via Folium | Free, no API key needed |
| Version control | Git + GitHub | Standard |
| Testing | pytest | Standard |
| Environment | `python-dotenv` for the Gemini key, `requirements.txt` pinned | Standard |

### Rationale for the constraints we're working under

The Gemini free tier (15 RPM, 1,000 RPD on Flash-Lite) is the binding constraint. Two consequences for the design:

1. **The LLM is a component, not the whole system.** Every agent does most of its work in deterministic Python (lookups, calculations, rule checks) and only uses the LLM to generate its *argument* — the 2-3 sentences explaining its position. This keeps LLM calls down and makes the agents genuinely reasoning systems rather than prompt wrappers.
2. **Caching is mandatory from day 1.** Cache by `(agent_name, candidate_route_hash)` so re-running the same debate during development doesn't hit the API at all. A demo-mode flag replays cached debates so a flaky network on demo day can't kill the presentation.

---

## 2. Repository Layout

```
manzil/
├── README.md
├── requirements.txt
├── .env.example                # GEMINI_API_KEY placeholder
├── .gitignore
│
├── data/                       # All knowledge bases (committed to repo)
│   ├── destinations.json       # The destination catalog
│   ├── case_base.json          # Past trips for CBR
│   ├── personas.json           # The 6 persona definitions used to generate cases
│   ├── costs.json              # Per-region per-season cost tables
│   ├── road_knowledge.json     # Pass closures, KKH segments, drive times
│   ├── safety_knowledge.json   # Altitude, NOC zones, hospitals
│   └── local_corpus/           # RAG source files for Local Experience Agent
│       ├── hunza/
│       ├── skardu/
│       └── ...
│
├── manzil/                     # The package
│   ├── __init__.py
│   ├── schemas.py              # Pydantic models for everything
│   ├── recommender/
│   │   ├── __init__.py
│   │   ├── filter.py           # Constraint-based filter
│   │   ├── cbr.py              # Case-based reasoning
│   │   ├── content.py          # Content-based scoring
│   │   ├── diversity.py        # Diversity-selection step (top-3)
│   │   ├── relaxation.py       # Constraint relaxation
│   │   └── pipeline.py         # End-to-end orchestration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseAgent class with shared LLM/cache logic
│   │   ├── weather.py
│   │   ├── road.py
│   │   ├── safety.py
│   │   ├── budget.py
│   │   ├── local.py
│   │   └── orchestrator.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── weather_api.py      # Open-Meteo wrapper
│   │   ├── cost_calc.py        # Deterministic cost decomposition
│   │   ├── route_calc.py       # Distance/drive-time lookup
│   │   ├── rag.py              # ChromaDB wrapper for Local Experience
│   │   └── cache.py            # File-backed LLM call cache
│   ├── graph/
│   │   ├── __init__.py
│   │   └── debate_graph.py     # The LangGraph state machine
│   ├── memory/
│   │   ├── __init__.py
│   │   └── feedback.py         # Post-trip rating → case base update
│   └── llm.py                  # Gemini client wrapper, cached
│
├── ui/
│   ├── app.py                  # Streamlit entrypoint
│   ├── pages/
│   │   ├── plan.py             # Form + candidate preview + debate visualization
│   │   └── feedback.py         # Post-trip rating form
│   └── components/
│       ├── map_view.py
│       ├── scorecard.py        # The agent scorecard widget
│       └── debate_trace.py     # Live debate animation
│
├── scripts/
│   ├── generate_case_base.py   # Persona-grounded synthetic generator
│   ├── build_rag_index.py      # Chunk + embed local_corpus into ChromaDB
│   └── seed_caches.py          # Pre-warm caches for demo mode
│
├── tests/
│   ├── test_filter.py
│   ├── test_cbr.py
│   ├── test_diversity.py
│   ├── test_orchestrator_policy.py
│   ├── test_scenarios.py       # End-to-end scenario tests
│   └── fixtures/               # Test queries and expected behaviours
│
└── eval/
    ├── ranking_metrics.py      # Precision@K, Recall@K, NDCG
    ├── relaxation_eval.py      # Over-constrained queries
    └── run_evaluation.py       # Produces tables for the report
```

The `manzil/` package is importable from anywhere — UI, scripts, tests, evaluation. Nothing in `ui/` or `scripts/` imports from `tests/`, and nothing in `manzil/` imports from `ui/` or `scripts/`. This is the dependency rule we enforce.

---

## 3. Data Schemas (the contracts that hold everything together)

All defined in `manzil/schemas.py` using Pydantic. These are the most important contracts in the system — get them right and the rest of the code falls into place.

### 3.1 Destination

```python
class Destination(BaseModel):
    id: str                             # "hunza-karimabad"
    name: str                           # "Karimabad, Hunza"
    region: str                         # "Gilgit-Baltistan"
    coords: Tuple[float, float]         # (lat, lon)
    altitude_m: int                     # 2,470
    terrain_tags: List[str]             # ["mountain", "valley"]
    activity_tags: List[str]            # ["cultural", "photography"]
    difficulty: int                     # 1-5
    cost_per_day: Dict[str, int]        # {"low": 4500, "mid": 8500, "high": 18000} PKR
    season_open: List[bool]             # 12-element vector, True if accessible that month
    group_suitability: List[str]        # ["solo", "couple", "family", "friends"]
    accessible: bool                    # wheelchair / elderly friendly
    noc_required_for_foreigners: bool
    description: str                    # short prose
```

### 3.2 RouteCandidate (what the recommender outputs)

```python
class RouteCandidate(BaseModel):
    candidate_id: str                   # "cand-A1"
    label: str                          # "Safe default — Hunza only via air"
    destinations: List[str]             # ordered list of Destination ids
    travel_modes: List[TravelMode]      # mode between each segment
    estimated_cost: int                 # PKR, total for the group
    days: int                           # total trip length
    diversity_axes: Dict[str, str]      # {"scope": "single-region", "pace": "relaxed", ...}
    cbr_score: float                    # 0-1
    content_score: float                # 0-1
    rationale: str                      # one-line justification for the user
```

### 3.3 UserQuery

```python
class UserQuery(BaseModel):
    group_size: int
    group_composition: GroupType        # solo | couple | family | friends | mixed
    budget_pkr: int
    days: int
    travel_month: int                   # 1-12
    travel_mode_pref: TravelMode        # road | air | hybrid
    origin_city: str
    style_tags: List[str]               # ["adventure", "cultural", ...]
    difficulty_tolerance: int           # 1-5
    preferred_destinations: List[str]   # optional, may be empty
    hard_constraints: List[str]         # ["wheelchair-accessible", "halal-food", ...]
```

### 3.4 AgentArgument (the structured argument format)

This is the most important schema. **Every specialist agent emits one of these per candidate.** The Orchestrator never sees prose alone — it sees structured arguments.

```python
class AgentArgument(BaseModel):
    agent_name: str                     # "WeatherAgent"
    candidate_id: str
    score: float                        # 0-10
    supporting_reasons: List[str]       # 2-3 short bullets, LLM-generated
    concerns: List[str]                 # 1-3 short bullets, LLM-generated
    hard_blocker: Optional[str]         # if set, the candidate is disqualified
    confidence: float                   # 0-1, agent's confidence in its assessment
    raw_data: Dict                      # the deterministic findings (for debugging/reporting)
```

### 3.5 DebateResult (what the Orchestrator outputs)

```python
class DebateResult(BaseModel):
    winner: RouteCandidate
    full_plan: DayByDayPlan             # the expanded itinerary
    scorecard: Dict[str, Dict[str, float]]   # {agent: {candidate_id: score}}
    blockers: Dict[str, List[str]]      # {candidate_id: [blocker_reasons]}
    dissenting_opinion: Optional[str]   # plain-language dissent, if any
    why_not: Dict[str, str]             # {runner_up_id: one-line explanation}
    orchestrator_reasoning: str         # the synthesis explanation
```

### 3.6 CaseBaseEntry

```python
class CaseBaseEntry(BaseModel):
    case_id: str
    query: UserQuery                    # the past traveller's query
    chosen_route: List[str]             # destination ids in order
    travel_modes: List[TravelMode]
    persona: str                        # which persona generated this
    rating: float                       # 1-5
    feedback_tags: List[str]            # ["loved-the-food", "too-rushed", ...]
    is_synthetic: bool                  # always True in the project version, important to track
```

---

## 4. The Recommender Pipeline (Stage 1)

`manzil/recommender/pipeline.py` exposes one function:

```python
def recommend(query: UserQuery) -> List[RouteCandidate]:
    """Returns exactly 3 diverse candidate routes."""
```

Internally:

1. **Constraint filter** (`filter.py`) — load all destinations, drop any that violate hard constraints (season closed, NOC issue, accessibility mismatch, group fit). Returns feasible destination set F.
2. **Route enumeration** — combinatorial generator that builds all reasonable destination sequences from F under the day budget. We cap at ~20 sequences via heuristics (max 4 destinations per trip, drive-time constraints between segments).
3. **CBR scoring** (`cbr.py`) — for each enumerated route, find k=10 nearest cases in the case base by weighted similarity over query attributes, score the route as the rating-weighted average of cases that visited a similar destination set.
4. **Content scoring** (`content.py`) — cosine similarity between user style/difficulty vector and aggregate destination feature vector for the route.
5. **Hybrid score**: `s = α · cbr + (1-α) · content`, with α=0.6 by default (tuned on the held-out split during evaluation).
6. **Constraint relaxation** (`relaxation.py`) — if step 1 produced an empty F (or step 2 produced no enumerable routes), relax in priority order: budget +15% first, then days -1, then preferred-destinations soft. Each relaxation reported to the user.
7. **Diversity selection** (`diversity.py`) — pick the top-1 route by hybrid score. Then iteratively pick 2 more routes that maximize a *combined score* of `(hybrid_score - λ · max_similarity_to_already_picked)`, where similarity is measured over the diversity axes (scope, mode mix, pace, risk, budget posture). λ=0.5 by default. This is a greedy MMR (Maximal Marginal Relevance) variant — standard, simple, and effective for our case.

Output: exactly 3 `RouteCandidate` objects, each tagged with the diversity axes it represents.

---

## 5. The LangGraph State Machine

`manzil/graph/debate_graph.py`. The whole debate is one graph.

### State definition

```python
class DebateState(TypedDict):
    query: UserQuery
    candidates: List[RouteCandidate]
    arguments: List[AgentArgument]      # accumulates as agents emit
    blockers: Dict[str, List[str]]
    result: Optional[DebateResult]
```

### Graph topology

```
                        ┌────────────┐
                        │   START    │
                        └──────┬─────┘
                               │
                        ┌──────▼──────┐
                        │  fan_out    │  (sets up parallel agent calls)
                        └──────┬──────┘
                               │
              ┌────────┬───────┼───────┬────────┐
              ▼        ▼       ▼       ▼        ▼
          [Weather] [Road] [Safety] [Budget] [Local]   ← parallel, 5 nodes
              │        │       │       │        │
              └────────┴───────┼───────┴────────┘
                               │
                        ┌──────▼──────┐
                        │ collect_args│  (waits for all 5)
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │ orchestrator│  (applies policy, picks winner, writes output)
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   END       │
                        └─────────────┘
```

### Key implementation notes

- **Parallelism** — LangGraph supports parallel branches via the conditional-edge pattern. We fan out from `fan_out` to all 5 agents in parallel; `collect_args` is a join node. This means a debate runs in roughly the time of the slowest single agent, not the sum of all 5.
- **Rate-limit awareness** — Flash-Lite is 15 RPM. If we run 5 agents in parallel and each does 1 LLM call, we use 5 of our 15 RPM. If a user fires 3 queries in a minute, we're at the limit. The graph has an internal rate limiter that throttles agent execution, falling back to sequential if needed. Most of the time this is invisible.
- **The Orchestrator node is the only LLM call that uses Flash, not Flash-Lite** — it's doing more synthesis. One Flash call per debate is well within Flash's 10 RPM / 250 RPD.
- **Error handling** — if an agent's LLM call fails (rate limit, network, parsing error), it returns a fallback `AgentArgument` with `confidence=0.0` and the error in `raw_data`. The Orchestrator weights low-confidence arguments down. The system never crashes mid-debate.

---

## 6. Agent Interface Contract

All agents inherit from `BaseAgent` (`manzil/agents/base.py`):

```python
class BaseAgent(ABC):
    name: str
    
    def evaluate(self, candidate: RouteCandidate, query: UserQuery) -> AgentArgument:
        # 1. Run deterministic analysis (Python-only, no LLM)
        analysis = self._analyze(candidate, query)
        
        # 2. Apply hard-blocker rules (Python-only, no LLM)
        blocker = self._check_blocker(analysis)
        
        # 3. Compute score from analysis (Python-only)
        score = self._score(analysis)
        
        # 4. Use LLM ONCE to generate the natural-language argument
        argument_text = self._llm_argue(analysis, score)
        
        return AgentArgument(
            agent_name=self.name,
            candidate_id=candidate.candidate_id,
            score=score,
            supporting_reasons=argument_text.reasons,
            concerns=argument_text.concerns,
            hard_blocker=blocker,
            confidence=self._confidence(analysis),
            raw_data=analysis.dict(),
        )
    
    @abstractmethod
    def _analyze(self, candidate, query): ...
    
    @abstractmethod
    def _check_blocker(self, analysis): ...
    
    @abstractmethod
    def _score(self, analysis): ...
    
    def _llm_argue(self, analysis, score):
        # Shared implementation: prompt template + Gemini call + parse + cache
        ...
```

**This is the key design discipline.** The LLM is called *once per agent per candidate, after all the real reasoning has already happened in Python*. Five agents × three candidates × one call each = **15 LLM calls per debate at most**. The Orchestrator adds 1 more call. Total: **16 calls per planning session**, which fits comfortably in our daily quota.

### Each specialist agent's `_analyze` does:

| Agent | What `_analyze` does |
|---|---|
| Weather | Open-Meteo API call for each destination + segment, plus seasonal pattern lookup from `road_knowledge.json` |
| Road | Lookup table check for each pass + each segment in the chosen month; drive-time computation from distance matrix |
| Safety | Altitude lookup vs group composition; NOC zone check; hospital/police-post lookup along the route |
| Budget | Deterministic cost decomposition: transport (per segment, per mode, per group size) + lodging (per night, per quality tier) + food + activities + buffer |
| Local | RAG retrieval over `local_corpus/` for each destination; aggregate retrieved chunks; if retrieval is empty for any destination, set `hard_blocker = None` but lower `confidence` and surface the gap honestly |

---

## 7. The Orchestrator's Policy

`manzil/agents/orchestrator.py` runs deterministic logic, then makes one LLM call for synthesis.

```python
def synthesize(self, candidates, arguments, blockers) -> DebateResult:
    # STEP 1: Eliminate candidates with hard blockers
    surviving = [c for c in candidates if c.candidate_id not in blockers or len(blockers[c.candidate_id]) == 0]
    
    if not surviving:
        return self._all_blocked_response(candidates, blockers)
    
    # STEP 2: Compute weighted aggregate score per surviving candidate
    weights = {
        "SafetyAgent": 0.30,
        "BudgetAgent": 0.25,
        "WeatherAgent": 0.20,
        "RoadAgent": 0.15,
        "LocalAgent": 0.10,
    }
    aggregate_scores = self._weighted_aggregate(surviving, arguments, weights)
    
    # STEP 3: Pick winner — with concentration tie-breaking
    winner = self._pick_winner(surviving, aggregate_scores, arguments)
    
    # STEP 4: Detect dissent
    dissent = self._detect_dissent(winner, arguments)
    
    # STEP 5: Generate why-not summaries
    why_not = self._generate_why_not(surviving, winner, arguments)
    
    # STEP 6: One LLM call for the natural-language synthesis
    reasoning = self._llm_synthesize(winner, arguments, dissent)
    
    # STEP 7: Build the day-by-day plan from the winner
    full_plan = self._expand_plan(winner, arguments)
    
    return DebateResult(...)
```

### Tie-breaking detail (the "concentration over breadth" rule)

When two candidates score within `epsilon = 0.3` of each other:

```python
def _concentration(arguments_for_candidate):
    scores = [arg.score for arg in arguments_for_candidate]
    return max(scores) - min(scores)   # higher = more concentrated strengths/weaknesses
```

The Orchestrator picks the higher-concentration candidate. Rationale: a route that one agent loves and one merely tolerates is more interesting than a route everyone shrugs at.

---

## 8. Tool Layer

`manzil/tools/`. The plumbing.

### Weather (`weather_api.py`)

Open-Meteo, free, no key, returns 16-day forecast and historical seasonal patterns.

```python
def get_forecast(lat: float, lon: float, start_date: date, days: int) -> WeatherData:
    # Hits api.open-meteo.com, parses JSON, returns structured WeatherData
    # Cached by (lat, lon, start_date) for 6 hours
```

### Cost calculator (`cost_calc.py`)

Pure Python over `costs.json`. Deterministic. No LLM.

```python
def estimate_cost(route: RouteCandidate, query: UserQuery) -> CostBreakdown:
    # Returns: transport, lodging, food, activities, buffer, total
```

### RAG (`rag.py`)

ChromaDB wrapper. Initialized once on app startup. Embeddings via Gemini's free embedding endpoint.

```python
def retrieve(destination_id: str, query_text: str, k: int = 5) -> List[Chunk]:
    # Returns up to k chunks. Empty list is a valid response.
    # The Local Experience Agent must handle empty retrieval gracefully — see ethics commitments.
```

### LLM cache (`cache.py`)

File-backed JSON cache, keyed by hash of `(model, prompt, temperature)`. Set `MANZIL_USE_CACHE=1` in dev to never miss; set `MANZIL_DEMO_MODE=1` to *only* use cache and refuse to call the API at all. Demo day always runs with `MANZIL_DEMO_MODE=1`.

---

## 9. Knowledge Bases — what's in each

### `destinations.json` (~10–15 entries)
The catalog. Manually curated. ~10–15 destinations is the in-scope target; team can extend later. Include at minimum: Hunza/Karimabad, Skardu, Naran, Fairy Meadows, Swat/Kalam, Murree, Deosai, Khaplu, Shogran, Neelum.

### `case_base.json` (~150 entries)
Generated by `scripts/generate_case_base.py`. Six personas × ~25 cases each, with controlled noise. Each persona has a defined preference distribution; cases are sampled by drawing constraints from the distribution and assigning a rating that's a noisy function of (preference-destination match).

### `costs.json`
Per region, per season (high/shoulder/low), per quality tier (low/mid/high). Transport costs separately, indexed by (origin, destination, mode). Manually compiled from public sources (PIA, Daewoo, etc.) with a "last_updated" field per row.

### `road_knowledge.json`
Per pass: `{name, altitude, open_months: [list], closure_risk_by_month: {...}}`. Per segment: `{from, to, distance_km, drive_time_hours, landslide_risk_by_month: {...}}`.

### `safety_knowledge.json`
Per destination: altitude, NOC requirement, nearest hospital, nearest police post. Plus rules: altitude-vs-group thresholds, generic risk warnings.

### `local_corpus/`
Per destination, ~5–15 short documents (food spots, viewpoints, cultural notes). Pass 1: scrape Wikivoyage and reputable Pakistani travel blogs, chunk to ~200 words. Pass 2 (during evaluation): curate based on observed retrieval failures.

---

## 10. Replanning Mechanism

Triggered by user input ("what if it rains on day 3?" / "what if my budget drops by 15%?").

Implementation: the disruption is a *modifier* to the original `UserQuery`. We construct a new query (`query_modified`) reflecting the disruption and re-run the entire pipeline (recommender → debate). The previous `DebateResult` is preserved in the UI so the user can compare.

Why a full re-run rather than incremental adjustment? Two reasons:
1. The debate is cheap (~16 LLM calls, mostly cached for similar contexts).
2. Incremental adjustment is much harder to get right — small disruptions can have large consequences (a closed pass eliminates entire routes), so a full re-run produces more honest results.

We will demonstrate one disruption scenario in the final demo: **"Day 3, the road to Skardu closed due to landslide. Replan."** The system re-runs, the Road Agent now flags the closure as a hard blocker on the original winner, a different candidate wins, and the user sees a side-by-side comparison.

---

## 11. Memory and Feedback Loop

`manzil/memory/feedback.py`. Light implementation, one cycle visible end-to-end.

After a "trip" (we'll simulate this in the UI with a time-skip button for demo purposes), the user opens the feedback page and rates the trip 1–5 with optional tags. This produces a new `CaseBaseEntry`:

```python
CaseBaseEntry(
    case_id=uuid,
    query=original_query,
    chosen_route=winning_route_destinations,
    travel_modes=winning_route_modes,
    persona="real_user",                # tagged as real, not synthetic
    rating=user_rating,
    feedback_tags=user_tags,
    is_synthetic=False,
)
```

This entry is appended to `case_base.json`. On the user's next query, the recommender's CBR step now includes this case. We demonstrate the loop by:
1. Running a query for User A → getting recommendation X
2. Simulating User A taking the trip and rating it 2/5 with tag "too rushed"
3. Running a similar query for a similar user → getting a different (slower-paced) recommendation, traceable back to User A's feedback

This is the demo of CLO-coverage Week 13 Memory module without expanding scope into a full longitudinal study.

---

## 12. UI Sketch (Streamlit)

### Page 1: `plan.py`

```
┌──────────────────────────────────────────────┐
│  Plan Your Trip                              │
│  ┌────────────────────────────────────────┐  │
│  │  Group size: [4]  Days: [7]            │  │
│  │  Budget (PKR): [120,000]               │  │
│  │  Travel month: [July]  Mode: [Road]    │  │
│  │  Origin: [Karachi]                     │  │
│  │  Style: [Adventure ▼] [Cultural ▼]     │  │
│  │  Difficulty: [3 ▼]                     │  │
│  │  [Plan my trip →]                      │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

After submit:

```
┌──────────────────────────────────────────────┐
│  3 routes generated.                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │ Route A │ │ Route B │ │ Route C │         │
│  │ map     │ │ map     │ │ map     │         │
│  │ summary │ │ summary │ │ summary │         │
│  └─────────┘ └─────────┘ └─────────┘         │
│                                              │
│  [Agents are debating... ●●●○○]              │
│  ↓                                           │
│  WINNER: Route B                             │
│  [day-by-day plan]                           │
│  [scorecard: agents × candidates]            │
│  [dissenting opinion box]                    │
│  [why-not for A and C]                       │
│  [Replan with disruption ▼]                  │
└──────────────────────────────────────────────┘
```

### Page 2: `feedback.py`

Simple form: rating slider, tag multi-select, free-text feedback. Submit appends to case base.

### Components worth calling out

- **`scorecard.py`** — a 5×3 heatmap table (5 agents × 3 candidates) with cell coloring by score. This is the single most demo-impressive widget and worth time on.
- **`debate_trace.py`** — a streaming animation where each agent's argument fades in as it's "completed." Cosmetic, but it makes the debate feel real.

---

## 13. Testing Strategy

Three layers, in order of priority:

### Unit tests (`tests/test_*.py`)
For each pure-Python module. Filter, CBR similarity, content scoring, diversity selection, cost calculator, road knowledge lookup. ~80% coverage target on `manzil/recommender/` and `manzil/tools/`.

### Scenario tests (`tests/test_scenarios.py`)
End-to-end: a fixed `UserQuery` runs through the full pipeline, and we assert properties of the result rather than exact outputs. Examples:
- "5-day Karachi-to-Skardu road trip in January" → all candidates have safety blockers → orchestrator returns the all-blocked response with reasons
- "7-day mid-budget Hunza trip in July, group of 4 friends" → exactly 3 candidates, all within budget+15%, scorecard populated, no nulls
- "Original plan winner" + "road closure disruption on day 3" → replan produces a different winner

We aim for ~12 scenarios. These are also our evaluation cases for the agent-behavior bucket.

### LLM output schema tests
Every LLM call goes through a parser that validates the response against a Pydantic schema. Failures retry once with a stricter prompt. After two failures, fall back. Tests include intentionally malformed LLM outputs (we replay cached bad outputs) to verify the fallback logic.

### What we explicitly don't test
- The LLM's *judgment* (we don't assert "Weather Agent must rate Route A higher than Route B"). LLM behaviour is a parameter of the system, not a unit-testable property.
- Visual UI rendering. Streamlit changes too fast and these tests are brittle.

---

## 14. Build Order (Week-by-Week)

This is the same timeline as the proposal but with concrete deliverables.

| Weeks | Deliverable | Owner |
|---|---|---|
| **1** | Repo skeleton, schemas defined, Gemini API key working, Open-Meteo working, ChromaDB installed, hello-world Streamlit page | Whole team |
| **2** | `destinations.json` with 10 entries; persona definitions; `costs.json`, `road_knowledge.json`, `safety_knowledge.json` first pass | Person 3 (Integration) leads |
| **3** | Constraint filter + content-based scoring, tested. `generate_case_base.py` produces 150 cases. | Person 1 (RS Lead) |
| **4** | CBR module with similarity function. Hybrid scorer. End-to-end recommender returns top-1. | Person 1 |
| **5** | Diversity selection (top-3 with MMR). Constraint relaxation. Recommender now returns 3 diverse candidates. **Mid-1 milestone.** | Person 1 |
| **6** | `BaseAgent` skeleton + caching. Weather Agent and Budget Agent fully implemented (including LLM `_argue`). | Person 2 (Agent Lead) |
| **7** | Road Agent, Safety Agent, Local Experience Agent (with RAG). Build RAG index from scraped corpus. | Person 2 |
| **8** | Orchestrator: aggregation, blockers, tie-breaking, dissent detection, why-not generation. LangGraph wiring, parallel execution. | Person 2 |
| **9** | UI plan page: form + 3-candidate preview + scorecard widget. Wire end-to-end. | Person 3 |
| **10** | Replanning mechanism: disruption input → modified query → re-run pipeline. Side-by-side comparison view. | Person 2 + Person 3 |
| **11** | Memory/feedback loop: feedback page, case base append, demonstrate visible-difference on next query. **Mid-2 milestone.** | Person 3 |
| **12** | Offline ranking evaluation: 80/20 split, Precision@K, NDCG, four configurations compared. | Person 1 |
| **13** | Scenario tests: 12 hand-crafted scenarios. User satisfaction survey (10-15 classmates). | Person 1 + Person 3 |
| **14** | RAG corpus curation pass (now informed by which retrievals failed). Demo mode (`MANZIL_DEMO_MODE=1`) seeded and verified. | Person 3 |
| **15** | Final report drafting. Presentation rehearsal. | Whole team |
| **16** | Submission, demo, defense. | Whole team |

### Why this ordering

- **Person 1 leads weeks 3–5.** They get the recommender working before the agents need to consume its output.
- **Person 2 takes weeks 6–8.** Agents are built on top of a stable recommender contract.
- **Person 3 owns the UI and integration in weeks 9–11.** They benefit from both layers being mature.
- **Weeks 12–14 are convergence and polish.** All three contribute.
- **Mid-1 (week 5) and Mid-2 (week 11) are real, demo-able milestones**, not paper deadlines. If a milestone slips, you know early.

### Critical-path risks

1. **CBR similarity function in week 4.** If the similarity metric doesn't produce sensible neighbors, the whole recommender produces noise. Plan B: fall back to content-only scoring with a stronger feature space.
2. **LangGraph parallelism in week 8.** Parallel execution is conceptually simple but the wiring can take a day to get right. Plan B: sequential execution. The system works the same; debates are just slower.
3. **RAG quality in week 7.** If scraped corpus is unusable, we'll have no choice but to manually curate ~50 entries. Build week-7 schedule with a 1-day buffer for this.

---

## 15. What Success Looks Like (concretely)

By the demo:

1. A user opens the UI, enters a real query, gets 3 visibly different candidates within ~30 seconds.
2. The agents debate, the scorecard fills in, a winner is picked, the dissenting opinion is sometimes non-trivial (i.e., it actually points at real trade-offs, not boilerplate).
3. The day-by-day plan is concrete: real destinations, plausible costs, sensible drive times, real weather and safety annotations.
4. The user clicks "what if there's a landslide on day 3?" The system replans, a different candidate wins, the user sees why.
5. The user rates the trip 2/5 "too rushed." A similar query from a similar user 30 seconds later produces a slower-paced recommendation.
6. The whole demo takes 8–10 minutes and the system never crashes, because demo mode is replaying cached debates.

If we hit all six of these, the project is genuinely done. Everything else is polish.

---

## Appendix: Day-1 Setup Commands

```bash
# Clone, create venv, install
git clone <repo>
cd manzil
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Get a Gemini key from https://aistudio.google.com/app/apikey
cp .env.example .env
# edit .env to add GEMINI_API_KEY=...

# Build initial knowledge bases (one-time)
python scripts/generate_case_base.py     # produces data/case_base.json
python scripts/build_rag_index.py        # produces ChromaDB index from data/local_corpus/

# Run the UI
streamlit run ui/app.py
```

---

*Document version: 1.0, working draft. Architecture and build plan, internal team reference. Not for submission.*
