# Manzil
## A Multi-Agent, Safety-First Travel Planner for Northern Pakistan

---

## 1. The Problem

Travelling from Karachi or Lahore to northern Pakistan Hunza, Skardu, Naran, Fairy Meadows, Swat is one of the most popular domestic trip patterns in the country, and one of the worst-served by technology.

A traveller planning such a trip today has three options, none of which work well:

**Option 1: Tour operators.** Apricot Tours, Pakistan Travel Guide, Exploria, dozens of others. They sell fixed packages with humans in the loop. They are reliable for a price, but they remove agency from the traveller, lock you into one company's network, and assume you have the budget for a full-service package. They are not intelligent, they are catalogues.

**Option 2: International AI travel tools.** Layla.ai, Wanderlog, ChatGPT, Gemini. These technically support Pakistan because they support every country, but they have no Pakistan-specific knowledge of any depth. They will happily generate an itinerary that includes Babusar Pass in late November (it closes in October). They will route you through Naran in monsoon without flagging landslide risk. They do not know what an NOC zone is. They are wide and shallow.

**Option 3: Manual research.** YouTube vlogs, Facebook groups (Backpacker's Pakistan, etc.), travel blogs of varying quality, asking friends who've been there. This is what most people actually do, and it is exhausting. The information is scattered, contradictory, and almost never updated for current road or weather conditions.

The result is that the average traveller plans a trip with significant unaddressed risks: routes that don't make sense for the season, budgets that quietly fail once real transport costs are added, no contingency for the road closures that happen *several times every year* on the Karakoram Highway, and no awareness of altitude or NOC requirements.

This is not a "convenience" problem. Northern Pakistan has real risks. Landslides on the KKH have killed travellers. Weather-stranded passes have left groups without supplies. Altitude sickness is common above 3,000 metres for travellers who didn't acclimatize. These are not edge cases — they are predictable, knowable, and routinely missed by the tools people currently use.

**The gap is specific:** there is no intelligent planning tool that combines (a) Pakistan-specific deterministic knowledge, (b) safety reasoning as a first-class concern, and (c) genuine personalization to the traveller's group, budget, and constraints.

---

## 2. The User

Manzil is built for a specific person first:

> A 22–35 year old domestic Pakistani — typically based in Karachi, Lahore, or Islamabad — planning a 5–10 day trip up north with friends or family. They have a rough budget, a window of available days, and a travel-mode preference (fly, drive, or some combination). They may already have a destination in mind (Hunza, Skardu) or be open to suggestions. They want a real plan they can act on, not a brochure.

This is the wedge user — sharp enough to design for, common enough to be a real market. Foreign tourists, the over-50 demographic, and luxury travellers are deliberately *not* the initial focus. They have different needs and we'll serve them better by serving the wedge user well first.

---

## 3. The Solution

Manzil is a two-stage system.

**Stage 1 — Recommendation.** A knowledge-based recommender takes the user's input (group size, days, budget, travel mode, optional preferred destinations, travel style, origin city) and produces **exactly three candidate routes**. Each candidate is a coherent trip skeleton — a set of destinations, a sequencing, a travel-mode mix, and a high-level cost estimate. The recommender produces three candidates rather than one because the next stage's whole point is to compare them, and three because that is enough to span a meaningful range of options without cluttering the debate.

Crucially, the three candidates are not minor variations of each other. They are deliberately diverse along meaningful axes — scope, pace, travel mode mix, risk profile, budget posture — so that the agents have real alternatives to argue between. This diversity requirement is part of the recommender's design and is described in detail in Section 4.

**Stage 2 — Multi-Agent Debate.** All three candidate routes are handed to a team of specialist agents. The user does not pre-select; the debate happens over the full set of three. Each agent argues for or against each candidate from its own domain expertise. A central Orchestrator agent moderates the debate, weighs the arguments, resolves disagreements, and produces a single final recommendation with a transparent justification — *why* the winning route won, *how each agent scored each candidate*, and *what the runner-ups offered differently*.

The two-stage design is deliberate. The recommender is good at narrowing the search space using user constraints and patterns from past travellers. The agentic layer is good at applying expert reasoning to a small number of distinct candidates. Trying to do both with one mechanism produces something that is mediocre at both. Splitting them lets each layer do what it is genuinely good at.

---

## 4. The Recommender (Stage 1)

The recommender is **knowledge-based**, specifically a hybrid of constraint-based filtering and case-based reasoning, with content-based scoring as a tiebreaker. We use this approach instead of collaborative filtering because:

- Travel is a low-frequency, high-stakes decision — users have no rating history at the time of asking.
- Hard constraints (budget, days, season, group composition, travel mode) dominate the decision and are non-negotiable.
- Deterministic Pakistani knowledge (which passes are open in which months, which routes are feasible in which weather) is more decision-relevant than statistical patterns.

**What it recommends:**
- **Destinations** — if the user hasn't picked any, or as additions/alternatives to what they did pick.
- **Timing** — within their available window, suggesting which days to allocate to which segments.
- **Route options** — three distinct ways of stitching the trip together, each represented as a sequence of destinations with travel modes between them.

**The diversity requirement.**
The recommender is explicitly designed to produce three candidates that differ along *meaningful axes*, not three near-duplicates. Without this, the downstream debate is meaningless: agents cannot have a real argument between five variants of the same trip. The axes the recommender uses to ensure diversity include:

- **Scope** — single-region (Hunza only) vs. multi-region (Hunza + Skardu, or Hunza + Naran)
- **Travel mode mix** — all-road vs. fly-and-road hybrid vs. fly-heavy
- **Pace** — relaxed (fewer destinations, more time per stop) vs. packed (more destinations, faster pace)
- **Risk profile** — conservative (well-trodden routes, lower altitude, easier roads) vs. ambitious (Fairy Meadows, Deosai, harder terrain)
- **Budget posture** — at-budget vs. budget-stretch (some routes only feasible at +10–15%, surfaced honestly with the relaxation reported to the user)

The recommender does not need to vary every axis on every query; it varies whichever axes produce three candidates that a human would describe as *meaningfully different*. A typical query might produce, for example: a "safe default" route, a "value pick" route, and an "ambitious option" route — but the actual axes used depend on what the user's constraints leave room for.

**How it works:**
- A constraint filter prunes infeasible candidates first (a 4-day Karachi-to-Skardu trip by road is removed up front; the user is told why).
- A case base of past trips built from a curated set of real travel reports plus persona-grounded synthetic profiles — provides similarity-based retrieval. New queries find their nearest analogues among past trips.
- A content-based scorer ranks remaining candidates on fit with the user's stated style preferences (adventure / cultural / photography / relaxation / family-friendly).
- A diversity-selection step then chooses the final three: starting from the top-ranked candidate and adding two more that maximize spread along the axes above. This is a small but important component — without it, the recommender would tend to produce three top-ranked-but-similar candidates and the debate would collapse.
- Each of the three candidates carries a justification ("similar travellers with your budget and group rated this 4.3/5; alternative route available if you can extend by 2 days").

**Constraint relaxation matters here.** When the user's constraints produce no feasible routes, the recommender doesn't fail silently — it relaxes the soft constraints in priority order and tells the user what it had to relax. ("No feasible routes for your budget. Showing options if you increase budget by 12%, or reduce days from 7 to 5.") This is the recommender's most distinctive behaviour and the thing that separates it from a search box.

---

## 5. The Multi-Agent Debate (Stage 2)

Once the recommender has produced three diverse candidate routes, all three go to the agent team. The user does not pre-select between them — that would defeat the purpose. The whole point of the debate is to surface trade-offs the user couldn't reasonably evaluate themselves, and to produce one final pick with full reasoning visible.

The team consists of:

**Specialist Agents**
- **Weather Agent** — checks forecast and seasonal patterns for each segment of each candidate. Flags weather windows, monsoon risk, snow/glacier conditions, flight cancellation likelihood for the relevant month. Calls a real weather API for current conditions; uses a static seasonal model for longer-range planning.
- **Road & Route Agent** — knows the state of the major highways and passes (KKH, Babusar, Lowari Tunnel, Khunjerab). Knows which mountain passes close in which months. Flags landslide-prone segments. Optimizes drive-time per day so the trip is humane (no 14-hour driving days).
- **Safety Agent** — tracks altitude exposure (Khunjerab is 4,693m; not safe for unacclimatized travellers, especially with kids or elderly). Flags NOC zones. Surfaces nearest hospitals and police posts along the route. Flags any current security advisories for specific districts.
- **Budget Agent** — decomposes each candidate into transport, lodging, food, activities, and buffer. Pulls from a static cost knowledge base (per region, per season, per quality tier). Reports honestly when a candidate is infeasible at the user's budget — including how much over.
- **Local Experience Agent** — surfaces genuine local recommendations beyond the standard tourist trail: food spots, viewpoints, cultural events, photography hours. Backed by a curated knowledge base (RAG-grounded) so it cannot hallucinate restaurants that don't exist.

**Orchestrator Agent**
The Orchestrator runs the debate. Each specialist evaluates *all three* candidates and emits a structured argument per candidate: a numerical score (0–10), the top supporting reasons, the top concerns, and any *hard blockers* (constraint violations that should disqualify the candidate outright — for example, a Safety Agent veto on a high-altitude pass for a group with children, or a Budget Agent veto when a route exceeds budget by more than the relaxation tolerance).

The Orchestrator then aggregates these arguments using a configurable policy:
- **Hard blockers eliminate.** Any candidate with one or more hard blockers is dropped from contention. If all three candidates are blocked, the Orchestrator reports the failure to the user with the reasons, rather than producing a bad recommendation. This is the safety-first commitment in action.
- **Weighted aggregation among survivors.** Surviving candidates are scored using domain-weighted aggregation, where the weights reflect Manzil's editorial priorities: Safety > Budget feasibility > Weather > Road conditions > Local Experience. These weights are fixed in the project version (the user does not set them) but the policy is explicit and documented.
- **Tie-breaking.** When two candidates score within a small epsilon, the Orchestrator picks the one with the most concentrated strengths over the one with broadly-okay-everywhere scores — that is, it prefers a route that is genuinely excellent on the things the user values to a route that is mediocre across the board.

**Why "debate" is the right metaphor**
The agents do not just fetch data and stuff it into a single prompt. Each one *argues a position* over a set of distinct alternatives. A candidate that the Weather Agent loves may be vetoed by the Safety Agent. The Local Experience Agent may rank a candidate first that the Budget Agent ranks last. The Orchestrator's job is to surface these disagreements rather than hide them — the user sees not just the answer but the disagreement that led to it.

This is where the agentic framing earns its keep. A single LLM call with all the data stuffed into the prompt could not produce this kind of transparent, multi-perspective reasoning, because there would be nothing forcing different perspectives to be represented separately. The architecture forces it.

### What the user sees

The Orchestrator's output is not just "Route 2 wins." It is a structured response with four parts:

1. **The winning route**, fully expanded into a day-by-day plan with all per-day annotations (weather, road, budget, local notes, safety flags).
2. **The agent scorecard** — a small matrix showing how each agent scored each of the three candidates. This is what makes the debate visible. The user sees, for example, that Route 1 was the Local Experience Agent's top pick but the Weather Agent's last; Route 2 won because it was no agent's top pick but no agent's last either; Route 3 was eliminated by a Safety Agent veto.
3. **The dissenting opinion** — if any agent strongly disagreed with the winning pick, the Orchestrator surfaces that disagreement explicitly. *"Note: the Local Experience Agent ranked Route 1 highest on cultural value. If cultural depth matters more to you than time efficiency, consider revisiting Route 1 — but be aware the Weather Agent flagged a 35% risk of flight cancellations on the return."* This is the system trusting the user with the actual trade-off rather than pretending it doesn't exist.
4. **The why-not summaries** — a one-line plain-language explanation for each runner-up: what it offered, why it lost, and under what conditions it might have won.

This turns the system from a black box that picks for you into a transparent decision-support tool that picks *with* you. It is more useful in practice and more impressive in a demo, and it is the single feature that most clearly differentiates Manzil from a search-style or single-shot LLM-style alternative.

---

## 6. Safety as a First-Class Concern

This is the differentiator. Most travel tools treat safety as small-print at the bottom of the itinerary. Manzil treats it as a hard constraint that gets a vote.

Concretely:
- The Safety Agent has *veto power*. If a route requires a high-altitude pass that is dangerous in the chosen month, no amount of budget-fit or experience-richness overrides that.
- Safety annotations appear on *every* recommendation, not just risky ones. The user always knows what they're walking into.
- The system *refuses* to recommend infeasible plans rather than silently producing bad ones. "There is no safe 5-day Skardu road trip in late January. Here is why, and here are alternatives."
- Hospital and police-post locations are surfaced for every overnight stop along the route.

Safety information is grounded in a curated knowledge base, not generated by the LLM. The agents reason over the knowledge — they do not invent it. This is the only acceptable architecture for safety-adjacent advice; we will not build a system that hallucinates a hospital location.

---

## 7. Memory and Adaptation (Lightweight)

After a trip, the user can rate the recommendation and leave brief feedback. This rating updates their profile in the case base and is reflected in their next query — different recommendations the second time, visibly improved fit. This closes the loop between recommendation and outcome and is the mechanism by which the system gets better over time.

In the project version this is implemented at light depth (one cycle visible end-to-end). In the startup extension, this becomes a real engine for personalization at scale.

---

## 8. What This Looks Like to the User

The user experience is deliberately simple:

1. User opens the app, fills a short form: people, days, budget, travel mode, optional preferred destinations, travel style, origin city.
2. Within seconds, the recommender produces three diverse candidate routes. The user briefly sees all three on a map with one-line summaries — but does not pick between them. The system itself will pick.
3. The agents debate. Each specialist scores all three candidates; the Orchestrator aggregates, applies safety vetoes, and selects a winner. The debate runs in seconds (or pseudo-live with a brief animation) and produces:
   - The winning route, fully expanded into a day-by-day plan
   - The agent scorecard showing how each agent rated each candidate
   - A dissenting opinion if any agent strongly disagreed
   - A why-not summary for the two runner-ups
4. The day-by-day plan shows: each day, each stop, estimated cost, weather note, road note, safety note, one local-experience tip per major stop.
5. The user can ask "what if it rains on day 3?" or "what if my budget drops by 15%?" and the system replans — re-running the recommender and re-running the debate over a fresh set of three candidates.
6. Post-trip, the user rates the trip. Their profile updates.

A working demo of this flow is what we will build in the project version. Steps 3 (the debate and its transparent outputs), 5 (replanning under disruption), and 6 (post-trip feedback) are the most technically interesting and will be shown clearly in the demonstration.

---

## 9. What's In Scope (Project Version) and What's Out

**In scope (16-week semester):**
- Curated dataset of ~10–15 northern destinations with rich attributes
- Knowledge-based recommender with constraint-based filtering, case-based reasoning, content-based scoring, and constraint relaxation
- Five specialist agents + one Orchestrator, built on LangGraph
- One real API integration (weather) to demonstrate live tool use
- RAG-grounded Local Experience Agent over a curated corpus
- Mid-trip replanning demonstrated for one disruption scenario
- Light memory/feedback loop
- Streamlit UI with map visualization
- Three-track evaluation: offline RS metrics, agent scenario tests, user satisfaction survey on classmates

**Out of scope for the project, in scope for the startup extension:**
- Real-time monitoring during the trip (push notifications, location-based alerts)
- Booking integration (hotels, flights, transport)
- Live road-condition feeds (would require partnerships with NHA or government data)
- Live security advisories (would require real-time intelligence sources)
- Foreign tourist mode with NOC application support
- Mobile app (the project ships as a web prototype)
- Payment integration
- Multi-language UI (Urdu, regional languages)
- Group collaboration (multiple users editing one trip)
- User-tunable agent priority weights — letting the user shift the Orchestrator's weighting (e.g., "I care most about cultural depth, less about budget"), so the debate outcome reflects what the specific user values. Fixed weights are sufficient for the project version.

This boundary is deliberate. Everything in the "out" list is what makes Manzil a startup rather than a project; trying to do them in the project version produces something that's bad at both.

---

## 10. Why It's Defensible (Project View)

As a project, Manzil hits a number of technically respectable points without being decorative:

- **Knowledge-based RS** is the right tool for the problem, not a forced fit — the structure of travel decisions genuinely calls for it.
- **Multi-agent debate over diverse candidates** is a meaningful use of agentic AI, not a wrapper around a single prompt. Three deliberately distinct candidates force the agents to argue between real alternatives; the Orchestrator's transparent output (winner, scorecard, dissent, why-not summaries) makes the multi-perspective reasoning visible to the user rather than hidden inside a single LLM call.
- **Real tool integration** (weather API) demonstrates genuine agent–environment interaction.
- **RAG with grounding and refusal** demonstrates principled handling of hallucination risk in safety-adjacent advice.
- **Constraint relaxation** is a non-trivial mechanism that produces visibly better behaviour than search-style alternatives.
- **The evaluation has both quantitative and qualitative components** — ranking metrics on synthetic data plus a real user survey.

A grader or external examiner watching the demo should walk away thinking: *this is a real system that does something useful, built on the right techniques, with honest acknowledgment of what is and isn't real yet.*

---

## 11. Why It's Defensible (Startup View)

If after the semester the team chooses to take it further, the startup case is:

- **Real, observable gap.** No Pakistan-specific intelligent planner exists. International tools are shallow; tour operators are not technological.
- **Wedge user is real and reachable.** Domestic Pakistani 22–35 year-olds planning northern trips are a large, English-speaking, smartphone-native, social-media-active group.
- **Safety differentiator is hard to copy.** A foreign tool can add Pakistan as a country, but they can't easily build the curated safety knowledge base or the agent logic without local expertise.
- **Multiple revenue paths exist:** affiliate commissions on bookings (transport, hotels), premium tier with live monitoring, B2B licensing to tour operators (we become their tech), B2B2C partnerships with telecoms or banks running travel-card promotions.
- **Path to defensibility:** the curated knowledge base + the user feedback loop + the safety knowledge become harder to replicate as the system runs longer. A clone with fewer trips and less feedback is structurally weaker.

This is not a pitch deck. It is enough to know that the project, if it works, has a real next step. We can talk about that next step seriously when the time comes.

---

## 12. Honest Acknowledgments

A few things we'd be calling out openly in the report and in any startup conversation:

- **Synthetic data limits the recommender's evaluation.** We can show the mechanics work; we cannot prove generalization to real travellers without real users. The user survey on classmates partially addresses this but is not a substitute.
- **The safety knowledge base is only as good as our curation.** We will document sources, dates, and our update process. This is a trust-building exercise, not a one-shot effort.
- **LLM hallucination risk is real even with RAG grounding.** We will implement explicit refusal mechanisms when retrieval is empty, but no system is hallucination-proof. The responsibility rests with the user to verify.
- **Live data is mocked or one-shot.** Real-time monitoring is a startup feature, not a project feature.
- **Personas embed our assumptions.** Six personas defined by us cannot represent every traveller. We document them, acknowledge the limitation, and measure recommendation diversity across personas.

These acknowledgments are part of the work, not weaknesses to hide. A system that knows what it doesn't know is more trustworthy than one that pretends to know everything.

----

*Document version: working draft, April 2026. Prepared for internal team discussion, not for submission.*
