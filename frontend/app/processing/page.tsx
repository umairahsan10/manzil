"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sun, Shield, Wallet, Route, Compass, Brain, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { planTrip } from "@/lib/api";
import { getPendingPlan, setLastTrip, setPendingPlan, clearPendingPlan } from "@/lib/storage";
import type { UserQuery } from "@/lib/types";
import { AgentCard, type AgentConfig, type AgentStatus } from "@/components/processing/AgentCard";

const AGENTS: AgentConfig[] = [
  { key: "weather", label: "Weather Agent", statusText: "Checking travel windows...", icon: Sun, color: "amber" },
  { key: "safety", label: "Safety Agent", statusText: "Evaluating route safety...", icon: Shield, color: "rose" },
  { key: "budget", label: "Budget Agent", statusText: "Calculating realistic costs...", icon: Wallet, color: "emerald" },
  { key: "road", label: "Route Agent", statusText: "Optimizing route efficiency...", icon: Route, color: "blue" },
  { key: "local", label: "Experience Agent", statusText: "Finding hidden experiences...", icon: Compass, color: "violet" },
];

const STAGGER_MS = 800;

export default function ProcessingPage() {
  const router = useRouter();
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>(
    AGENTS.map(() => "pending")
  );
  const [orchestratorStatus, setOrchestratorStatus] = useState<AgentStatus>("pending");
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  const runPlanning = useCallback(
    async (query: UserQuery) => {
      const startTime = Date.now();
      const timers: ReturnType<typeof setTimeout>[] = [];

      AGENTS.forEach((_, idx) => {
        timers.push(
          setTimeout(() => {
            setAgentStatuses((prev) => {
              const next = [...prev];
              next[idx] = "active";
              return next;
            });
          }, idx * STAGGER_MS)
        );

        timers.push(
          setTimeout(() => {
            setAgentStatuses((prev) => {
              const next = [...prev];
              next[idx] = "done";
              return next;
            });
          }, (idx + 1) * STAGGER_MS)
        );
      });

      try {
        const response = await planTrip(query);

        const allDoneTime = AGENTS.length * STAGGER_MS + 400;
        const elapsed = Date.now() - startTime;
        const waitMore = Math.max(0, allDoneTime - elapsed);

        await new Promise((resolve) => setTimeout(resolve, waitMore));

        setOrchestratorStatus("active");
        await new Promise((resolve) => setTimeout(resolve, 1500));
        setOrchestratorStatus("done");

        setLastTrip(response);
        setPendingPlan(query, response);

        await new Promise((resolve) => setTimeout(resolve, 800));
        router.push("/results");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Planning failed");
        setAgentStatuses(AGENTS.map(() => "done"));
      } finally {
        timers.forEach(clearTimeout);
      }
    },
    [router]
  );

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const pending = getPendingPlan();
    if (!pending?.query) {
      router.push("/plan");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    runPlanning(pending.query);
  }, [router, runPlanning]);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center pt-20 px-4">
        <div className="glass-card rounded-3xl p-8 max-w-md text-center">
          <div className="flex h-16 w-16 mx-auto items-center justify-center rounded-2xl bg-destructive/10 mb-4">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <h2 className="font-display text-xl font-bold mb-2">Planning failed</h2>
          <p className="text-sm text-muted-foreground mb-6">{error}</p>
          <button
            onClick={() => {
              clearPendingPlan();
              router.push("/plan");
            }}
            className="rounded-xl bg-primary text-primary-foreground px-6 py-3 text-sm font-bold hover:bg-primary/90 transition-all"
          >
            Back to Canvas
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pt-20 overflow-hidden">
      {/* Cinematic backdrop */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 animate-gradient" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/10 blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-accent/10 blur-3xl animate-float-soft" />
      </div>

      <div className="container relative z-10 py-8">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 rounded-full glass px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4">
            <Brain className="h-3.5 w-3.5 text-primary animate-pulse" />
            AI Analysis in Progress
          </div>
          <h1 className="text-4xl font-display font-bold tracking-tight sm:text-5xl">
            Five agents are analyzing your trip
          </h1>
          <p className="mt-3 text-lg text-muted-foreground">
            Each specialist evaluates every candidate route independently
          </p>
        </div>

        {/* Center: animated map placeholder + agent cards */}
        <div className="max-w-3xl mx-auto">
          {/* Animated route visualization */}
          <div className="relative h-48 mb-8 glass-card rounded-3xl overflow-hidden flex items-center justify-center">
            <div className="absolute inset-0 flex items-center justify-center">
              <svg width="80%" height="100%" viewBox="0 0 600 180" fill="none">
                {/* Route lines */}
                <path
                  d="M 50 90 Q 200 30, 350 90 T 550 90"
                  stroke="url(#routeGrad)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  className="animate-route-draw"
                />
                <path
                  d="M 50 110 Q 200 170, 350 110 T 550 110"
                  stroke="#D97706"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeDasharray="5 5"
                  opacity="0.5"
                  className="animate-route-draw"
                  style={{ animationDelay: "0.5s" }}
                />
                <defs>
                  <linearGradient id="routeGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#15803D" />
                    <stop offset="100%" stopColor="#2563EB" />
                  </linearGradient>
                </defs>
                {/* Stop dots */}
                {[50, 300, 550].map((x, idx) => (
                  <circle
                    key={x}
                    cx={x}
                    cy={90}
                    r="6"
                    fill={idx === 0 ? "#15803D" : idx === 2 ? "#2563EB" : "#FFFFFF"}
                    stroke={idx === 1 ? "#15803D" : "none"}
                    strokeWidth="2"
                    className="animate-agent-pulse"
                    style={{ animationDelay: `${idx * 0.3}s` }}
                  />
                ))}
              </svg>
            </div>
            <div className="absolute bottom-3 left-4 text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Candidate routes
            </div>
          </div>

          {/* Agent cards */}
          <div className="space-y-3">
            {AGENTS.map((agent, idx) => (
              <AgentCard
                key={agent.key}
                config={agent}
                status={agentStatuses[idx]}
                delay={idx * 50}
              />
            ))}
          </div>

          {/* Orchestrator finale */}
          <div
            className={cn(
              "mt-6 transition-all duration-700",
              orchestratorStatus === "pending"
                ? "opacity-0 scale-90 pointer-events-none h-0 overflow-hidden"
                : "opacity-100 scale-100"
            )}
          >
            <div
              className={cn(
                "glass-strong rounded-3xl p-6 transition-all",
                orchestratorStatus === "active" && "border-glow shadow-xl",
                orchestratorStatus === "done" && "border-glow shadow-xl"
              )}
            >
              <div className="flex items-center gap-4">
                <div
                  className={cn(
                    "flex h-14 w-14 items-center justify-center rounded-2xl transition-all",
                    orchestratorStatus === "active" && "bg-primary text-primary-foreground animate-pulse-glow",
                    orchestratorStatus === "done" && "bg-primary text-primary-foreground"
                  )}
                >
                  <Brain className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-display text-lg font-bold">Orchestrator Agent</h3>
                  <p
                    className={cn(
                      "text-sm mt-0.5",
                      orchestratorStatus === "done" ? "text-primary font-semibold" : "text-muted-foreground"
                    )}
                  >
                    {orchestratorStatus === "done"
                      ? "Your best trip is ready"
                      : "Comparing all candidate routes and finalizing your best trip..."}
                  </p>
                </div>
                <div
                  className={cn(
                    "h-7 w-7 rounded-full transition-all",
                    orchestratorStatus === "done" && "bg-primary text-primary-foreground flex items-center justify-center"
                  )}
                >
                  {orchestratorStatus === "done" && (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
