"use client";

import { useState } from "react";
import {
  Trophy,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Calendar,
  Wallet,
  Route,
  Car,
  Plane,
  CircleDot,
  Brain,
  ChevronDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DebateResult, RouteCandidate, AgentArgument } from "@/lib/types";
import { getRouteStops, getDestinationName } from "@/lib/destinations";
import { RouteMap, MapStop } from "@/components/route-map";
import { PexelsImage } from "@/components/pexels-image";

function getAgentArgs(
  args: Record<string, AgentArgument[]> | AgentArgument[] | undefined,
  agent: string
): AgentArgument[] {
  if (!args) return [];
  if (Array.isArray(args)) return args.filter((a) => a.agent_name === agent);
  return args[agent] || [];
}

const agentMeta: Record<string, { label: string; emoji: string; color: string; bar: string }> = {
  weather: { label: "Weather", emoji: "☀️", color: "text-amber-600 bg-amber-50", bar: "bg-amber-500" },
  road: { label: "Road", emoji: "🛣️", color: "text-stone-600 bg-stone-100", bar: "bg-stone-500" },
  safety: { label: "Safety", emoji: "🛡️", color: "text-rose-600 bg-rose-50", bar: "bg-rose-500" },
  budget: { label: "Budget", emoji: "💰", color: "text-emerald-700 bg-emerald-50", bar: "bg-emerald-600" },
  local: { label: "Local", emoji: "🗺️", color: "text-sky-600 bg-sky-50", bar: "bg-sky-500" },
};

function formatRouteLabel(candidate: RouteCandidate): string {
  if (candidate.label) return candidate.label;
  const route = candidate.route || candidate.destinations || [];
  return route.map(getDestinationName).join(" → ") || candidate.candidate_id;
}

function routeStops(candidate: RouteCandidate): string[] {
  return candidate.route || candidate.destinations || [];
}

function formatTravelMode(mode: string) {
  if (mode === "road") return { icon: Car, label: "Road" };
  if (mode === "air") return { icon: Plane, label: "Flight" };
  return { icon: CircleDot, label: "Hybrid" };
}

export function RouteHero({
  candidate,
  isWinner,
  mapStops,
}: {
  candidate: RouteCandidate;
  isWinner?: boolean;
  mapStops: MapStop[];
}) {
  const cost = candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0;
  const days = candidate.days ?? routeStops(candidate).length;
  const stops = routeStops(candidate);

  return (
    <div className="relative overflow-hidden rounded-[2.5rem] shadow-2xl">
      <div className="relative h-[500px] lg:h-[600px]">
        <RouteMap
          stops={mapStops}
          height="100%"
          className="absolute inset-0 rounded-none"
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />

        <div className="absolute bottom-0 left-0 right-0 p-6 lg:p-10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              {isWinner && (
                <Badge className="mb-3 w-fit gap-1.5 rounded-full bg-primary px-4 py-1.5 text-xs font-bold text-primary-foreground">
                  <Trophy className="h-3.5 w-3.5" /> Recommended route
                </Badge>
              )}
              <h2 className="text-3xl font-extrabold text-white text-shadow sm:text-4xl lg:text-5xl">
                {formatRouteLabel(candidate)}
              </h2>
              <p className="mt-2 max-w-lg text-white/80 text-shadow-sm">
                {candidate.rationale || `A ${days}-day route through northern Pakistan.`}
              </p>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                {stops.map((stop, idx) => (
                  <div key={stop} className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20 text-xs font-bold text-white backdrop-blur-sm">
                      {idx + 1}
                    </span>
                    <span className="text-sm font-medium text-white text-shadow-sm">
                      {getDestinationName(stop)}
                    </span>
                    {idx < stops.length - 1 && (
                      <span className="text-white/40">→</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="pointer-events-auto flex flex-wrap gap-3">
              <div className="rounded-2xl bg-white/10 px-5 py-3 text-center backdrop-blur-md">
                <Calendar className="mx-auto h-5 w-5 text-white" />
                <p className="mt-1 text-xl font-bold text-white">{days}</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-white/70">Days</p>
              </div>
              <div className="rounded-2xl bg-white/10 px-5 py-3 text-center backdrop-blur-md">
                <Wallet className="mx-auto h-5 w-5 text-white" />
                <p className="mt-1 text-xl font-bold text-white">PKR {(cost / 1000).toFixed(0)}k</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-white/70">Estimated</p>
              </div>
              <div className="rounded-2xl bg-white/10 px-5 py-3 text-center backdrop-blur-md">
                <Route className="mx-auto h-5 w-5 text-white" />
                <p className="mt-1 text-xl font-bold text-white">{stops.length}</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-white/70">Stops</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CandidateSelector({
  candidates,
  selectedId,
  winnerId,
  onSelect,
}: {
  candidates: RouteCandidate[];
  selectedId: string;
  winnerId?: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-primary">
            Compare routes
          </p>
          <h3 className="text-2xl font-extrabold">All candidates</h3>
        </div>
      </div>
      <div className="flex gap-4 overflow-x-auto pb-4 pt-2">
        {candidates.map((candidate) => {
          const isSelected = candidate.candidate_id === selectedId;
          const isWinner = candidate.candidate_id === winnerId;
          const cost = candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0;
          const stops = routeStops(candidate);
          const firstStop = stops[0];

          return (
            <button
              key={candidate.candidate_id}
              onClick={() => onSelect(candidate.candidate_id)}
              className={`group relative flex-shrink-0 w-60 overflow-hidden rounded-3xl border-2 text-left transition-all ${
                isSelected
                  ? "border-primary shadow-xl"
                  : "border-transparent bg-card shadow-md hover:shadow-lg"
              }`}
            >
              <div className="relative h-32 overflow-hidden">
                <PexelsImage
                  query={firstStop ? getDestinationName(firstStop) + " Pakistan" : "Pakistan mountains"}
                  alt={formatRouteLabel(candidate)}
                  containerClassName="absolute inset-0"
                  className="transition-transform duration-700 group-hover:scale-110"
                  overlay={
                    <div className="absolute inset-0 bg-gradient-to-t from-card via-card/30 to-transparent" />
                  }
                />
                {isWinner && (
                  <div className="absolute left-3 top-3 flex items-center gap-1 rounded-full bg-primary px-2.5 py-1 text-[10px] font-bold text-primary-foreground">
                    <Trophy className="h-3 w-3" /> Winner
                  </div>
                )}
              </div>
              <div className="p-4">
                <p className="font-bold line-clamp-1">{formatRouteLabel(candidate)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {stops.length} stops · PKR {cost.toLocaleString()}
                </p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {stops.slice(0, 3).map((stop) => (
                    <span
                      key={stop}
                      className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground"
                    >
                      {getDestinationName(stop).split(",")[0].trim()}
                    </span>
                  ))}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function AgentScorecard({ debate }: { debate: DebateResult }) {
  const agents = Object.keys(debate.scorecard || {});
  const candidates = agents.length > 0 ? Object.keys(debate.scorecard[agents[0]] || {}) : [];

  if (agents.length === 0 || candidates.length === 0) return null;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-primary">Agent insights</p>
        <h3 className="text-2xl font-extrabold">How each specialist voted</h3>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => {
          const meta = agentMeta[agent] || { label: agent, emoji: "🤖", color: "bg-muted", bar: "bg-muted-foreground" };
          return (
            <div key={agent} className="rounded-3xl border border-border bg-card p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <span className="text-2xl">{meta.emoji}</span>
                <h4 className="text-lg font-bold">{meta.label}</h4>
              </div>
              <div className="space-y-3">
                {candidates.map((cand) => {
                  const score = debate.scorecard[agent][cand];
                  const blocked =
                    debate.blockers?.[cand]?.includes(agent) ||
                    getAgentArgs(debate.arguments, agent).some((a) => a.candidate_id === cand && a.hard_blocker);
                  return (
                    <div key={cand} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-semibold text-muted-foreground">{cand}</span>
                        {blocked ? (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-600">
                            <XCircle className="h-3 w-3" /> Blocked
                          </span>
                        ) : (
                          <span className="font-bold">{score > 0 ? score.toFixed(1) : "—"}</span>
                        )}
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={`h-full rounded-full ${meta.bar} transition-all duration-700`}
                          style={{ width: blocked ? "0%" : `${Math.max(score * 10, 0)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function WhyNotList({ debate }: { debate: DebateResult }) {
  const entries = Object.entries(debate.why_not || {});
  if (entries.length === 0) return null;
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-primary">Runner-ups</p>
        <h3 className="text-2xl font-extrabold">Why not these?</h3>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {entries.map(([cand, reason]) => (
          <div key={cand} className="rounded-3xl border border-border bg-card p-6 shadow-sm">
            <p className="text-lg font-bold">{cand}</p>
            <p className="mt-2 text-muted-foreground leading-relaxed">{reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DissentBox({ debate }: { debate: DebateResult }) {
  if (!debate.dissenting_opinion) return null;
  return (
    <div className="rounded-3xl border border-amber-200 bg-amber-50/70 p-6">
      <div className="flex gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-amber-900">Dissenting opinion</h4>
          <p className="mt-1 text-sm text-amber-800/80 leading-relaxed">{debate.dissenting_opinion}</p>
        </div>
      </div>
    </div>
  );
}

export function OrchestratorReasoning({ reasoning }: { reasoning?: string }) {
  if (!reasoning) return null;
  return (
    <div className="rounded-3xl border border-border bg-card p-8 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Brain className="h-5 w-5" />
        </div>
        <h3 className="text-xl font-bold">Orchestrator reasoning</h3>
      </div>
      <p className="text-muted-foreground leading-relaxed">{reasoning}</p>
    </div>
  );
}

export function DeveloperDetails({
  result,
}: {
  result: { recommendation_trace?: unknown; debate_trace?: unknown };
}) {
  const hasTrace = Boolean(result.recommendation_trace || result.debate_trace);
  if (!hasTrace) return null;

  return (
    <details className="group rounded-3xl border border-border bg-card overflow-hidden shadow-sm">
      <summary className="cursor-pointer list-none flex items-center justify-between p-6 hover:bg-muted/30 transition-colors">
        <span className="font-bold">Developer details</span>
        <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="px-6 pb-6 space-y-4">
        {result.recommendation_trace ? (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">
              Recommendation trace
            </h4>
            <pre className="text-xs overflow-auto bg-muted rounded-2xl p-4 max-h-[300px]">
              {JSON.stringify(result.recommendation_trace, null, 2)}
            </pre>
          </div>
        ) : null}
        {result.debate_trace ? (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">
              Debate trace
            </h4>
            <pre className="text-xs overflow-auto bg-muted rounded-2xl p-4 max-h-[300px]">
              {JSON.stringify(result.debate_trace, null, 2)}
            </pre>
          </div>
        ) : null}
      </div>
    </details>
  );
}

export function ItineraryPreview({ candidate }: { candidate: RouteCandidate }) {
  const stops = routeStops(candidate);
  if (stops.length === 0) return null;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-primary">Itinerary</p>
        <h3 className="text-2xl font-extrabold">Day by day</h3>
      </div>
      <div className="relative">
        <div className="absolute left-6 top-4 bottom-4 w-px bg-border" />
        <div className="space-y-4">
          {stops.map((stop, idx) => {
            const dest = getDestinationName(stop);
            return (
              <div key={stop} className="relative flex gap-5 rounded-3xl border border-border bg-card p-5 shadow-sm">
                <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-lg font-bold">{dest}</h4>
                  <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
                    Explore {dest}, local viewpoints, and nearby attractions.
                  </p>
                </div>
                <div className="hidden sm:block h-16 w-24 overflow-hidden rounded-2xl">
                  <PexelsImage
                    query={dest + " Pakistan"}
                    alt={dest}
                    containerClassName="h-full w-full"
                    className="h-full w-full"
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export { getRouteStops };
