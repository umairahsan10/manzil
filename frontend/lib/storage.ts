/**
 * Typed localStorage helpers for saving, sharing, and retrieving trips.
 * No auth — trips are device-local.
 */

import type { PlanResponse, RouteCandidate, UserQuery } from "./types";

const LAST_TRIP_KEY = "manzil:last-trip";
const SAVED_TRIPS_KEY = "manzil:saved-trips";
const PENDING_PLAN_KEY = "manzil:pending-plan";

export interface SavedTrip {
  trip_id: string;
  candidate_id: string;
  saved_at: string;
  label: string;
  estimated_cost: number;
  days: number;
  query: UserQuery;
  response: PlanResponse;
}

export function getLastTrip(): PlanResponse | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(LAST_TRIP_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PlanResponse;
  } catch {
    return null;
  }
}

export function setLastTrip(trip: PlanResponse): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(LAST_TRIP_KEY, JSON.stringify(trip));
}

export function getSavedTrips(): SavedTrip[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(SAVED_TRIPS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as SavedTrip[];
  } catch {
    return [];
  }
}

export function saveTrip(
  tripId: string,
  candidate: RouteCandidate,
  query: UserQuery,
  response: PlanResponse
): SavedTrip {
  const saved: SavedTrip = {
    trip_id: tripId,
    candidate_id: candidate.candidate_id,
    saved_at: new Date().toISOString(),
    label: candidate.label || candidate.destinations.join(" → "),
    estimated_cost: candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0,
    days: candidate.days ?? 0,
    query,
    response,
  };
  const trips = getSavedTrips().filter((t) => t.candidate_id !== saved.candidate_id);
  trips.unshift(saved);
  if (typeof window !== "undefined") {
    localStorage.setItem(SAVED_TRIPS_KEY, JSON.stringify(trips.slice(0, 20)));
  }
  return saved;
}

export function removeSavedTrip(candidateId: string): void {
  if (typeof window === "undefined") return;
  const trips = getSavedTrips().filter((t) => t.candidate_id !== candidateId);
  localStorage.setItem(SAVED_TRIPS_KEY, JSON.stringify(trips));
}

export function isTripSaved(candidateId: string): boolean {
  return getSavedTrips().some((t) => t.candidate_id === candidateId);
}

/**
 * Build a shareable URL for a trip with query params.
 */
export function buildShareUrl(
  tripId: string,
  candidateId: string,
  query: UserQuery
): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams({
    trip: tripId,
    candidate: candidateId,
    origin: query.origin_city,
    budget: query.budget_pkr.toString(),
    days: query.days.toString(),
    month: query.travel_month.toString(),
    group: query.group_composition,
    size: query.group_size.toString(),
  });
  return `${window.location.origin}/trip/${candidateId}?${params.toString()}`;
}

/**
 * Share a trip via the Web Share API, falling back to clipboard copy.
 */
export async function shareTrip(
  tripId: string,
  candidateId: string,
  query: UserQuery,
  label: string
): Promise<"shared" | "copied" | "failed"> {
  const url = buildShareUrl(tripId, candidateId, query);
  const shareData = {
    title: `Manzil — ${label}`,
    text: `Check out this trip plan: ${label}`,
    url,
  };

  if (typeof navigator !== "undefined" && navigator.share) {
    try {
      await navigator.share(shareData);
      return "shared";
    } catch {
      return "failed";
    }
  }

  if (typeof navigator !== "undefined" && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(url);
      return "copied";
    } catch {
      return "failed";
    }
  }

  return "failed";
}

/**
 * Store a pending plan (query + response) for navigation between pages
 * (e.g. /plan → /processing → /results → /trip/[id]).
 */
export function setPendingPlan(query: UserQuery, response?: PlanResponse): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(PENDING_PLAN_KEY, JSON.stringify({ query, response }));
}

export function getPendingPlan(): { query: UserQuery; response?: PlanResponse } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PENDING_PLAN_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearPendingPlan(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(PENDING_PLAN_KEY);
}
