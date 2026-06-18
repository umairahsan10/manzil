// Phase 1: hand-written TypeScript types mirroring manzil/schemas.py.
// Phase 2: these will be generated from the FastAPI OpenAPI spec.

export interface HealthResponse {
  status: string;
  cache_enabled: boolean;
  demo_mode: boolean;
  full_llm_mode: boolean;
  cache_dir: string;
  llm: {
    ok: boolean;
    message: string;
    keys: Array<{
      index: number;
      available: boolean;
      calls_today: number;
      last_error: string | null;
    }>;
  };
  weather: {
    ok: boolean;
    message: string;
  };
}

export type TravelMode = "road" | "air" | "hybrid";
export type GroupType = "solo" | "couple" | "family" | "friends" | "mixed";
export type DisruptionKind =
  | "road_closed"
  | "budget_cut"
  | "weather_event"
  | "flight_cancelled";

export interface UserQuery {
  group_size: number;
  group_composition: GroupType;
  budget_pkr: number;
  days: number;
  travel_month: number;
  travel_mode_pref: TravelMode;
  origin_city: string;
  style_tags: string[];
  difficulty_tolerance: number;
  preferred_destinations?: string[];
  hard_constraints?: string[];
  is_foreign_traveller: boolean;
  elderly_in_group: boolean;
}

export interface Disruption {
  kind: DisruptionKind;
  day_index?: number;
  pct_cut?: number;
  pass_id?: string;
  destination_id?: string;
  description?: string;
}

export interface PlanRequest {
  query: UserQuery;
  full_llm_mode?: boolean;
}

export interface PlanResponse {
  trip_id: string;
  query: UserQuery;
  candidates: RouteCandidate[];
  recommendation_trace?: RecommendationTrace;
  debate_result?: DebateResult;
}

export interface RouteCandidate {
  candidate_id: string;
  label?: string;
  route?: string[];
  destinations: string[];
  travel_modes: TravelMode[];
  estimated_cost?: number;
  total_cost_pkr?: number;
  days?: number;
  score?: number;
  tags?: string[];
  diversity_axes?: Record<string, string>;
  rationale?: string;
  why?: string;
}

export interface RecommendationTrace {
  filter?: {
    total_destinations: number;
    feasible_count: number;
    dropped_count: number;
    dropped_summary: Record<string, number>;
  };
  enumerate?: {
    total_routes_generated: number;
    single_stop_routes: number;
    multi_stop_routes: number;
  };
  cbr?: {
    top_k: Array<{
      route_id: string;
      similarity: number;
      rating: number;
    }>;
  };
  content?: {
    tag_vector: Record<string, number>;
  };
  hybrid?: {
    cbr_weight: number;
    content_weight: number;
  };
  diversity?: {
    axes: string[];
    mmr_steps: Array<{
      route_id: string;
      mmr_score: number;
    }>;
  };
  relaxation_note?: string;
}

export interface AgentArgument {
  agent_name: string;
  candidate_id: string;
  score: number;
  supporting_reasons: string[];
  concerns: string[];
  hard_blocker: string | null;
  confidence: number;
}

export interface OrchestratorTrace {
  candidates: string[];
  surviving_ids: string[];
  blocked_ids: string[];
  tie_break: unknown;
  dissent: {
    threshold: number;
    dissent_lines: string[];
    had_dissent: boolean;
  };
  why_not: unknown[];
  weights_used: Record<string, number>;
  final_winner_id: string | null;
}

export interface DebateTrace {
  arguments: AgentArgument[];
  orchestrator: OrchestratorTrace;
}

export interface DebateResult {
  winner: RouteCandidate | null;
  runner_ups: RouteCandidate[];
  scorecard: Record<string, Record<string, number>>;
  blockers: Record<string, string[]>;
  arguments: Record<string, AgentArgument[]> | AgentArgument[];
  dissenting_opinion: string | null;
  why_not: Record<string, string>;
  all_blocked?: boolean;
  orchestrator_reasoning?: string;
  debate_trace?: DebateTrace;
}

export interface DayStop {
  destination_id: string;
  name: string;
  activities: string[];
  local_tips: string[];
}

export interface DayPlan {
  day: number;
  travel_mode: TravelMode;
  drive_time_minutes: number;
  day_budget_pkr: number;
  safety_notes: string[];
  weather_notes: string[];
  road_notes: string[];
  stops: DayStop[];
}

export interface DayByDayPlan {
  days: DayPlan[];
}

export interface FeedbackRequest {
  trip_id: string;
  rating: number;
  tags: string[];
  comment?: string;
}

export interface FeedbackResponse {
  feedback_id: string;
  message: string;
}

export interface FeedbackStatsResponse {
  count: number;
  avg_rating: number;
  top_tags: string[];
}

// Utility constants
export const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const TRAVEL_MODES: { value: TravelMode; label: string }[] = [
  { value: "road", label: "Road" },
  { value: "air", label: "Air" },
  { value: "hybrid", label: "Hybrid" },
];

export const GROUP_TYPES: { value: GroupType; label: string }[] = [
  { value: "solo", label: "Solo" },
  { value: "couple", label: "Couple" },
  { value: "family", label: "Family" },
  { value: "friends", label: "Friends" },
  { value: "mixed", label: "Mixed" },
];

export const ORIGIN_CITIES = ["karachi", "lahore", "islamabad"];

export const STYLE_TAGS = [
  "adventure",
  "relaxing",
  "scenic",
  "cultural",
  "food",
  "photography",
  "trekking",
  "luxury",
];
