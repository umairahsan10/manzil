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
  // New planning toggles (Phase 2 UI redesign)
  kids_in_group: boolean;
  altitude_sensitive: boolean;
  luxury_stays_needed: boolean;
  motion_sickness: boolean;
  road_trip_only: boolean;
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

export interface PreviewResponse {
  trip_id: string | null;
  top: RouteCandidate | null;
  candidates: RouteCandidate[];
  rough_scores: {
    safety: number;
    weather: number;
    budget_fit: number;
    trip_score: number;
  } | null;
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

// --- New structured types for the trip detail page ---

export interface DayWeatherCard {
  destination_id: string;
  temp_high_c: number | null;
  temp_low_c: number | null;
  precip_prob_pct: number | null;
  precip_mm: number | null;
  summary: string;
  condition: string; // "Excellent" | "Good" | "Fair" | "Poor"
}

export interface RoadRiskCard {
  segment: string;
  risk_level: string; // "low" | "moderate" | "high"
  reasons: string[];
}

export interface DayStop {
  destination_id: string;
  name: string;
  activities: string[];
  local_tips: string[];
  local_tip?: string | null;
}

export interface DayPlan {
  day: number;
  day_index?: number;
  travel_mode: TravelMode | null;
  drive_time_minutes: number;
  drive_time_hours?: number | null;
  day_budget_pkr: number;
  estimated_cost?: number;
  safety_notes: string[];
  weather_notes: string[];
  road_notes: string[];
  safety_note?: string | null;
  weather_note?: string | null;
  road_note?: string | null;
  stops: DayStop[];
  // New structured fields
  stay_type?: string | null;
  altitude_m?: number | null;
  weather?: DayWeatherCard | null;
  road_risk?: RoadRiskCard | null;
}

export interface DayByDayPlan {
  candidate_id: string;
  days: DayPlan[];
  total_cost: number;
}

export interface AltitudePoint {
  day: number;
  destination_id: string;
  destination_name: string;
  altitude_m: number;
}

export interface FacilityProximity {
  destination_id: string;
  name: string;
  distance_km: number;
  level: string;
}

export interface SafetyAnalysis {
  altitude_progression: AltitudePoint[];
  road_risk_cards: RoadRiskCard[];
  hospital_proximity: FacilityProximity[];
  police_stations: FacilityProximity[];
  emergency_contacts: Array<Record<string, string>>;
  max_altitude_m: number;
  applied_threshold_m: number;
  threshold_label: string;
}

export interface ExperienceSpot {
  name: string;
  destination_id: string;
  category: string;
  description: string;
  source: string;
}

export interface ExperienceLayer {
  hidden_spots: ExperienceSpot[];
  local_foods: ExperienceSpot[];
  sunrise_points: ExperienceSpot[];
  photo_spots: ExperienceSpot[];
}

export interface CostBreakdownDetailed {
  transport: number;
  lodging: number;
  food: number;
  activities: number;
  buffer: number;
  total: number;
}

export interface DebateResult {
  winner: RouteCandidate | null;
  full_plan?: DayByDayPlan | null;
  runner_ups: RouteCandidate[];
  scorecard: Record<string, Record<string, number>>;
  blockers: Record<string, string[]>;
  arguments: Record<string, AgentArgument[]> | AgentArgument[];
  dissenting_opinion: string | null;
  why_not: Record<string, string>;
  all_blocked?: boolean;
  orchestrator_reasoning?: string;
  debate_trace?: DebateTrace;
  // New structured layers
  safety_analysis?: SafetyAnalysis | null;
  experience_layer?: ExperienceLayer | null;
  cost_breakdown?: CostBreakdownDetailed | null;
}

export interface FeedbackRequest {
  trip_id: string;
  rating: number;
  budget_accuracy?: number;
  safety_accuracy?: number;
  experience_quality?: number;
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
  { value: "air", label: "Flight" },
  { value: "hybrid", label: "Mixed" },
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

// New: intensity spectrum (maps 1:1 to difficulty_tolerance 1-5)
export const INTENSITY_LEVELS = [
  { value: 1, label: "Chill" },
  { value: 2, label: "Relaxed" },
  { value: 3, label: "Balanced" },
  { value: 4, label: "Packed" },
  { value: 5, label: "Extreme" },
] as const;

// New: UI display names for agents (backend keys stay road/local)
export const AGENT_DISPLAY: Record<string, { label: string; backend: string }> = {
  weather: { label: "Weather Agent", backend: "weather" },
  safety: { label: "Safety Agent", backend: "safety" },
  budget: { label: "Budget Agent", backend: "budget" },
  road: { label: "Route Agent", backend: "road" },
  local: { label: "Experience Agent", backend: "local" },
  orchestrator: { label: "Orchestrator Agent", backend: "orchestrator" },
};

// New: feedback tags for the redesigned feedback page
export const FEEDBACK_TAGS = [
  { value: "would-recommend", label: "Would recommend", emoji: "👍" },
  { value: "great-views", label: "Great views", emoji: "🏔️" },
  { value: "loved-the-food", label: "Loved the food", emoji: "🍲" },
  { value: "family-friendly", label: "Family friendly", emoji: "👨‍👩‍👧‍👦" },
  { value: "too-rushed", label: "Too rushed", emoji: "⏱️" },
  { value: "too-slow", label: "Too slow", emoji: "🐢" },
  { value: "weather-was-wrong", label: "Weather was wrong", emoji: "🌧️" },
  { value: "budget-overran", label: "Overspent", emoji: "💸" },
  { value: "road-was-rough", label: "Road blocked", emoji: "🛣️" },
  { value: "stay-mismatch", label: "Stay mismatch", emoji: "🏨" },
  { value: "not-again", label: "Not again", emoji: "👎" },
];

// New: default query for the planning canvas
export const DEFAULT_QUERY: UserQuery = {
  group_size: 4,
  group_composition: "family",
  budget_pkr: 150000,
  days: 7,
  travel_month: 7,
  travel_mode_pref: "road",
  origin_city: "islamabad",
  style_tags: ["scenic", "cultural"],
  difficulty_tolerance: 3,
  is_foreign_traveller: false,
  elderly_in_group: false,
  kids_in_group: false,
  altitude_sensitive: false,
  luxury_stays_needed: false,
  motion_sickness: false,
  road_trip_only: false,
};
