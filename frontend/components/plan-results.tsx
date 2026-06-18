"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { DebateResult, RouteCandidate, AgentArgument } from "@/lib/types";

function getAgentArgs(
  args: Record<string, AgentArgument[]> | AgentArgument[] | undefined,
  agent: string
): AgentArgument[] {
  if (!args) return [];
  if (Array.isArray(args)) return args.filter((a) => a.agent_name === agent);
  return args[agent] || [];
}

const agentLabels: Record<string, string> = {
  weather: "Weather",
  road: "Road",
  safety: "Safety",
  budget: "Budget",
  local: "Local Experience",
};

const agentColors: Record<string, string> = {
  weather: "bg-sky-500",
  road: "bg-amber-500",
  safety: "bg-rose-500",
  budget: "bg-emerald-500",
  local: "bg-violet-500",
};

function scoreColor(score: number): string {
  if (score >= 7) return "text-emerald-600 bg-emerald-50";
  if (score >= 4) return "text-amber-600 bg-amber-50";
  return "text-rose-600 bg-rose-50";
}

export function CandidateCard({
  candidate,
  isWinner,
}: {
  candidate: RouteCandidate;
  isWinner?: boolean;
}) {
  const cost = candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0;
  const route = candidate.route || candidate.destinations || [];
  return (
    <Card
      className={
        isWinner
          ? "border-primary/40 ring-2 ring-primary/20 bg-primary/[0.02]"
          : "border-border/60"
      }
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            {isWinner && (
              <Badge className="mb-1 gap-1">
                <CheckCircle2 className="h-3 w-3" /> Winner
              </Badge>
            )}
            <CardTitle className="text-base leading-snug">
              {candidate.label || route.join(" → ")}
            </CardTitle>
            <CardDescription className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
              <span>{candidate.days ?? route.length} stops</span>
              <span>·</span>
              <span>PKR {cost.toLocaleString()}</span>
              {candidate.travel_modes && (
                <>
                  <span>·</span>
                  <span className="capitalize">
                    {candidate.travel_modes.join("/")}
                  </span>
                </>
              )}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-1.5">
          {route.map((stop, idx) => (
            <span key={idx} className="text-xs">
              <span
                className={
                  idx === 0
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                }
              >
                {stop}
              </span>
              {idx < route.length - 1 && (
                <span className="text-muted-foreground/50 mx-1.5">→</span>
              )}
            </span>
          ))}
        </div>
        {candidate.why && (
          <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
            {candidate.why}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function AgentScorecard({
  debate,
}: {
  debate: DebateResult;
}) {
  const agents = Object.keys(debate.scorecard || {});
  const candidates = agents.length > 0 ? Object.keys(debate.scorecard[agents[0]] || {}) : [];

  if (agents.length === 0 || candidates.length === 0) {
    return null;
  }

  return (
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-lg">Agent Scorecard</CardTitle>
        <CardDescription>
          How each specialist agent scored every candidate route.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/60">
                <th className="text-left font-medium text-muted-foreground py-2.5 pr-4">
                  Agent
                </th>
                {candidates.map((cand) => (
                  <th
                    key={cand}
                    className="text-center font-medium text-muted-foreground py-2.5 px-3"
                  >
                    {cand}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent} className="border-b border-border/40 last:border-0">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${agentColors[agent] || "bg-muted-foreground"}`}
                      />
                      <span className="font-medium">
                        {agentLabels[agent] || agent}
                      </span>
                    </div>
                  </td>
                  {candidates.map((cand) => {
                    const score = debate.scorecard[agent][cand];
                    const blocked =
                      debate.blockers?.[cand]?.includes(agent) ||
                      getAgentArgs(debate.arguments, agent).some(
                        (a) =>
                          a.candidate_id === cand && a.hard_blocker
                      );
                    return (
                      <td key={cand} className="text-center py-3 px-3">
                        {blocked ? (
                          <span className="inline-flex items-center justify-center gap-1 rounded-md bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-600">
                            <XCircle className="h-3 w-3" />
                            Blocked
                          </span>
                        ) : (
                          <span
                            className={`inline-flex items-center justify-center rounded-md px-2 py-1 text-xs font-semibold ${scoreColor(score)}`}
                          >
                            {score?.toFixed(1) ?? "—"}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export function DissentBox({ debate }: { debate: DebateResult }) {
  if (!debate.dissenting_opinion) return null;
  return (
    <Card className="border-amber-200 bg-amber-50/50">
      <CardContent className="flex gap-3 pt-6">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-sm text-amber-900">
            Dissenting opinion
          </h4>
          <p className="mt-1 text-sm text-amber-800/80">
            {debate.dissenting_opinion}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function WhyNotList({ debate }: { debate: DebateResult }) {
  const entries = Object.entries(debate.why_not || {});
  if (entries.length === 0) return null;
  return (
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-lg">Why not the runner-ups?</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([cand, reason]) => (
          <div key={cand} className="flex gap-3">
            <Badge variant="outline" className="shrink-0">
              {cand}
            </Badge>
            <p className="text-sm text-muted-foreground">{reason}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
