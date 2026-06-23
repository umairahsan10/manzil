"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Trophy, Calendar, Wallet, Shield, Sun, Zap, Bookmark, BookmarkCheck, Share2, GitCompare, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { getPendingPlan, saveTrip, shareTrip, setLastTrip } from "@/lib/storage";
import type { PlanResponse, RouteCandidate, UserQuery, DebateResult } from "@/lib/types";
import { getRouteStops, getDestinationShortName, deriveTripName, deriveBadges, deriveFatigue } from "@/lib/destinations";
import { RouteMap } from "@/components/route-map";

export default function ResultsPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [query, setQuery] = useState<UserQuery | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [compareList, setCompareList] = useState<Set<string>>(new Set());
  const [showCompare, setShowCompare] = useState(false);

  useEffect(() => {
    const pending = getPendingPlan();
    if (!pending?.response) {
      router.push("/plan");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlan(pending.response);
    setQuery(pending.query);
    setLastTrip(pending.response);
    const winnerId = pending.response.debate_result?.debate_trace?.orchestrator?.final_winner_id;
    setSelectedId(winnerId || pending.response.candidates[0]?.candidate_id || "");
  }, [router]);

  if (!plan || !query) return null;

  const debate = plan.debate_result;
  const candidates = plan.candidates;
  const winnerId = debate?.debate_trace?.orchestrator?.final_winner_id;
  const allBlocked = debate?.all_blocked;

  const selected = candidates.find((c) => c.candidate_id === selectedId) || candidates[0];
  const selectedStops = selected ? getRouteStops(selected.destinations) : [];

  const handleSave = (candidate: RouteCandidate) => {
    if (savedIds.has(candidate.candidate_id)) {
      setSavedIds((prev) => {
        const next = new Set(prev);
        next.delete(candidate.candidate_id);
        return next;
      });
    } else {
      saveTrip(plan.trip_id, candidate, query, plan);
      setSavedIds((prev) => new Set(prev).add(candidate.candidate_id));
    }
  };

  const handleShare = async (candidate: RouteCandidate) => {
    await shareTrip(plan.trip_id, candidate.candidate_id, query, deriveTripName(candidate));
  };

  const toggleCompare = (id: string) => {
    setCompareList((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 3) {
        next.add(id);
      }
      return next;
    });
  };

  if (allBlocked) {
    return (
      <div className="min-h-screen bg-background pt-24 px-4">
        <div className="max-w-2xl mx-auto glass-card rounded-3xl p-8 text-center">
          <div className="flex h-16 w-16 mx-auto items-center justify-center rounded-2xl bg-destructive/10 mb-4">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <h1 className="font-display text-2xl font-bold mb-2">No viable route found</h1>
          <p className="text-muted-foreground mb-6">
            {debate?.orchestrator_reasoning || "All candidates were blocked. Try adjusting your budget or constraints."}
          </p>
          <button
            onClick={() => router.push("/plan")}
            className="rounded-xl bg-primary text-primary-foreground px-6 py-3 text-sm font-bold hover:bg-primary/90 transition-all"
          >
            Back to Canvas
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="container">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 rounded-full glass px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
            <Trophy className="h-3.5 w-3.5 text-primary" />
            Your Plans
          </div>
          <h1 className="text-4xl font-display font-bold tracking-tight sm:text-5xl">
            Here&apos;s what the agents decided
          </h1>
          <p className="mt-3 text-lg text-muted-foreground">
            {candidates.length} candidate routes were debated by 5 specialist agents
          </p>
        </div>

        {/* Top: interactive route map */}
        {selectedStops.length > 0 && (
          <div className="mb-8 glass-card rounded-3xl overflow-hidden">
            <div className="relative h-[400px]">
              <RouteMap stops={selectedStops} height="100%" className="rounded-none border-none" variant="primary" />
              <div className="pointer-events-none absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/60 to-transparent">
                <div className="flex items-center gap-2">
                  {selected.candidate_id === winnerId && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-bold text-primary-foreground">
                      <Trophy className="h-3 w-3" /> Recommended
                    </span>
                  )}
                  <h2 className="font-display text-2xl font-bold text-white text-shadow">
                    {deriveTripName(selected)}
                  </h2>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Trip cards */}
        <div className="mb-8">
          <h3 className="font-display text-xl font-bold mb-4">Trip Options</h3>
          <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
            {candidates.map((candidate) => (
              <TripCard
                key={candidate.candidate_id}
                candidate={candidate}
                isWinner={candidate.candidate_id === winnerId}
                isSelected={candidate.candidate_id === selectedId}
                isSaved={savedIds.has(candidate.candidate_id)}
                isInCompare={compareList.has(candidate.candidate_id)}
                query={query}
                debate={debate}
                onSelect={() => setSelectedId(candidate.candidate_id)}
                onSave={() => handleSave(candidate)}
                onShare={() => handleShare(candidate)}
                onCompare={() => toggleCompare(candidate.candidate_id)}
                onViewDetails={() => router.push(`/trip/${candidate.candidate_id}`)}
              />
            ))}
          </div>
        </div>

        {/* Compare tray */}
        {compareList.size > 0 && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40">
            <div className="glass-strong rounded-2xl px-5 py-3 shadow-2xl flex items-center gap-4">
              <span className="text-sm font-bold">{compareList.size} selected to compare</span>
              <button
                onClick={() => setShowCompare(true)}
                className="rounded-xl bg-primary text-primary-foreground px-4 py-2 text-xs font-bold hover:bg-primary/90 transition-all"
              >
                Compare Now
              </button>
              <button
                onClick={() => setCompareList(new Set())}
                className="text-xs font-semibold text-muted-foreground hover:text-foreground"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* Comparison table */}
        {candidates.length > 1 && (
          <ComparisonTable candidates={candidates} query={query} debate={debate} winnerId={winnerId} />
        )}

        {/* Compare modal */}
        {showCompare && (
          <CompareModal
            candidates={candidates.filter((c) => compareList.has(c.candidate_id))}
            query={query}
            debate={debate}
            onClose={() => setShowCompare(false)}
          />
        )}
      </div>
    </div>
  );
}

function TripCard({
  candidate,
  isWinner,
  isSelected,
  isSaved,
  isInCompare,
  query,
  debate,
  onSelect,
  onSave,
  onShare,
  onCompare,
  onViewDetails,
}: {
  candidate: RouteCandidate;
  isWinner: boolean;
  isSelected: boolean;
  isSaved: boolean;
  isInCompare: boolean;
  query: UserQuery;
  debate?: DebateResult;
  onSelect: () => void;
  onSave: () => void;
  onShare: () => void;
  onCompare: () => void;
  onViewDetails: () => void;
}) {
  const cost = candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0;
  const days = candidate.days ?? 0;
  const stops = candidate.destinations;
  const badges = deriveBadges(candidate, query);
  const tripName = deriveTripName(candidate);

  // Scores from debate
  const scorecard = debate?.scorecard || {};
  const safetyScore = avgScore(scorecard, "SafetyAgent", candidate.candidate_id);
  const weatherScore = avgScore(scorecard, "WeatherAgent", candidate.candidate_id);
  const fatigue = deriveFatigue(undefined, days);

  return (
    <div
      onClick={onSelect}
      className={cn(
        "flex-shrink-0 w-72 glass-card rounded-3xl overflow-hidden cursor-pointer transition-all",
        isSelected ? "ring-2 ring-primary border-glow" : "hover:shadow-lg"
      )}
    >
      {/* Card header */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            {isWinner && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2.5 py-1 text-[10px] font-bold text-primary-foreground mb-2">
                <Trophy className="h-3 w-3" /> Winner
              </span>
            )}
            <h4 className="font-display text-lg font-bold tracking-tight">{tripName}</h4>
          </div>
        </div>

        {/* Route */}
        <div className="flex items-center flex-wrap gap-1 mb-4">
          {stops.map((stop, idx) => (
            <div key={stop} className="flex items-center gap-1">
              <span className="text-xs font-semibold text-muted-foreground">
                {getDestinationShortName(stop)}
              </span>
              {idx < stops.length - 1 && <span className="text-muted-foreground/40">→</span>}
            </div>
          ))}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <Stat icon={Calendar} label="Days" value={`${days}`} />
          <Stat icon={Wallet} label="Budget" value={`PKR ${(cost / 1000).toFixed(0)}k`} />
          <Stat
            icon={Shield}
            label="Safety"
            value={safetyScore > 0 ? `${Math.round(safetyScore * 10)}%` : "—"}
            color="text-primary"
          />
          <Stat
            icon={Sun}
            label="Weather"
            value={weatherScore > 0 ? weatherLabel(weatherScore) : "—"}
            color="text-accent"
          />
        </div>

        {/* Fatigue */}
        <div className="flex items-center gap-2 mb-4">
          <Zap className="h-3.5 w-3.5 text-warning" />
          <span className="text-xs font-semibold text-muted-foreground">Fatigue:</span>
          <span className="text-xs font-bold">{fatigue}</span>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {badges.map((badge) => (
            <span
              key={badge}
              className="rounded-full bg-secondary px-2.5 py-1 text-[10px] font-bold text-foreground"
            >
              {badge}
            </span>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="px-5 pb-5 flex items-center gap-2">
        <button
          onClick={(e) => { e.stopPropagation(); onViewDetails(); }}
          className="flex-1 rounded-xl bg-primary text-primary-foreground px-3 py-2 text-xs font-bold hover:bg-primary/90 transition-all"
        >
          View Details
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onCompare(); }}
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-xl transition-all",
            isInCompare ? "bg-accent text-accent-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
          )}
          title="Compare"
        >
          <GitCompare className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onSave(); }}
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-xl transition-all",
            isSaved ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
          )}
          title="Save"
        >
          {isSaved ? <BookmarkCheck className="h-3.5 w-3.5" /> : <Bookmark className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onShare(); }}
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-secondary text-muted-foreground hover:text-foreground transition-all"
          title="Share"
        >
          <Share2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl bg-secondary/60 p-2.5">
      <div className="flex items-center gap-1.5">
        <Icon className={cn("h-3.5 w-3.5 text-muted-foreground", color)} />
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{label}</span>
      </div>
      <p className={cn("text-sm font-bold mt-1", color)}>{value}</p>
    </div>
  );
}

function ComparisonTable({
  candidates,
  query,
  debate,
  winnerId,
}: {
  candidates: RouteCandidate[];
  query: UserQuery;
  debate?: DebateResult;
  winnerId?: string | null;
}) {
  const scorecard = debate?.scorecard || {};
  const rows = [
    { label: "Cost", extract: (c: RouteCandidate) => `PKR ${((c.estimated_cost ?? c.total_cost_pkr ?? 0) / 1000).toFixed(0)}k` },
    { label: "Weather", extract: (c: RouteCandidate) => weatherLabel(avgScore(scorecard, "WeatherAgent", c.candidate_id)) },
    { label: "Risk", extract: (c: RouteCandidate) => riskLabel(avgScore(scorecard, "SafetyAgent", c.candidate_id)) },
    { label: "Comfort", extract: (c: RouteCandidate) => comfortLabel(avgScore(scorecard, "RoadAgent", c.candidate_id)) },
    { label: "Adventure", extract: (c: RouteCandidate) => adventureLabel(avgScore(scorecard, "LocalAgent", c.candidate_id)) },
  ];

  return (
    <div className="glass-card rounded-3xl overflow-hidden">
      <div className="p-5 border-b border-border/60">
        <h3 className="font-display text-lg font-bold">Quick Comparison</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border/60">
              <th className="text-left p-4 text-xs font-bold uppercase tracking-widest text-muted-foreground">Metric</th>
              {candidates.map((c) => (
                <th key={c.candidate_id} className="text-center p-4 text-xs font-bold">
                  {c.candidate_id === winnerId && <Trophy className="inline h-3 w-3 text-primary mr-1" />}
                  {deriveTripName(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-border/40 last:border-0">
                <td className="p-4 text-sm font-semibold text-muted-foreground">{row.label}</td>
                {candidates.map((c) => (
                  <td key={c.candidate_id} className="text-center p-4 text-sm font-bold">
                    {row.extract(c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CompareModal({
  candidates,
  query,
  debate,
  onClose,
}: {
  candidates: RouteCandidate[];
  query: UserQuery;
  debate?: DebateResult;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="glass-strong rounded-3xl p-6 max-w-3xl w-full max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-display text-xl font-bold">Compare Trips</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-xl">✕</button>
        </div>
        <div className={cn("grid gap-4", candidates.length === 2 ? "grid-cols-2" : "grid-cols-1 md:grid-cols-3")}>
          {candidates.map((c) => {
            const cost = c.estimated_cost ?? c.total_cost_pkr ?? 0;
            return (
              <div key={c.candidate_id} className="glass-card rounded-2xl p-5">
                <h4 className="font-display font-bold mb-3">{deriveTripName(c)}</h4>
                <div className="space-y-2 text-sm">
                  <Row label="Cost" value={`PKR ${cost.toLocaleString()}`} />
                  <Row label="Days" value={`${c.days ?? 0}`} />
                  <Row label="Stops" value={`${c.destinations.length}`} />
                  <Row label="Route" value={c.destinations.map(getDestinationShortName).join(" → ")} />
                  <Row label="Highlights" value={c.rationale || "—"} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{label}</span>
      <span className="font-semibold text-sm">{value}</span>
    </div>
  );
}

function avgScore(scorecard: Record<string, Record<string, number>>, agent: string, candidateId: string): number {
  const agentScores = scorecard[agent];
  if (!agentScores || !agentScores[candidateId]) return 0;
  return agentScores[candidateId] / 10; // normalize 0-10 to 0-1
}

function weatherLabel(score: number): string {
  if (score === 0) return "—";
  if (score >= 0.75) return "Excellent";
  if (score >= 0.55) return "Good";
  if (score >= 0.35) return "Fair";
  return "Poor";
}

function riskLabel(score: number): string {
  if (score === 0) return "—";
  if (score >= 0.75) return "Low";
  if (score >= 0.55) return "Moderate";
  return "High";
}

function comfortLabel(score: number): string {
  if (score === 0) return "—";
  if (score >= 0.75) return "High";
  if (score >= 0.55) return "Moderate";
  return "Low";
}

function adventureLabel(score: number): string {
  if (score === 0) return "—";
  if (score >= 0.7) return "High";
  if (score >= 0.5) return "Medium";
  return "Low";
}
