import {
  DebateResult,
  Disruption,
  FeedbackRequest,
  FeedbackResponse,
  FeedbackStatsResponse,
  HealthResponse,
  PlanRequest,
  PlanResponse,
  RouteCandidate,
  UserQuery,
} from "@/lib/types";

const API_BASE = "/api/v1";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export async function planTrip(
  query: UserQuery,
  fullLlmMode: boolean = false
): Promise<PlanResponse> {
  return fetchJson<PlanResponse>("/plan", {
    method: "POST",
    body: JSON.stringify({ query, full_llm_mode: fullLlmMode }),
  });
}

export function streamPlanTrip(
  query: UserQuery,
  fullLlmMode: boolean = false,
  onEvent: (event: StreamEvent) => void,
  onError: (error: Error) => void
): () => void {
  const url = new URL(`${API_BASE}/plan/stream`, window.location.origin);
  const eventSource = new EventSource(url.toString());

  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onEvent(parsed);
    } catch {
      onEvent({ type: "raw", data: event.data });
    }
  };

  eventSource.onerror = () => {
    onError(new Error("SSE connection error"));
    eventSource.close();
  };

  return () => eventSource.close();
}

export type StreamEvent =
  | { type: "agent_done"; agent: string; arguments: unknown }
  | { type: "orchestrator_done"; result: DebateResult }
  | { type: "raw"; data: string };

export async function replanTrip(
  tripId: string,
  disruption: Disruption
): Promise<{
  trip_id: string;
  original_result: { candidates: RouteCandidate[]; debate_result: DebateResult };
  new_result: { candidates: RouteCandidate[]; debate_result: DebateResult };
}> {
  return fetchJson("/replan", {
    method: "POST",
    body: JSON.stringify({ trip_id: tripId, disruption }),
  });
}

export async function submitFeedback(
  request: FeedbackRequest
): Promise<FeedbackResponse> {
  return fetchJson<FeedbackResponse>("/feedback", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getFeedbackStats(): Promise<FeedbackStatsResponse> {
  return fetchJson<FeedbackStatsResponse>("/feedback/stats");
}
