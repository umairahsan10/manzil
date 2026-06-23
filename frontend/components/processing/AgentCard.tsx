"use client";

import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type AgentStatus = "pending" | "active" | "done";

export interface AgentConfig {
  key: string;
  label: string;
  statusText: string;
  icon: React.ElementType;
  color: "emerald" | "blue" | "amber" | "rose" | "stone" | "violet";
}

const colorMap = {
  emerald: { bg: "bg-primary", text: "text-primary", glow: "border-glow", ring: "ring-primary/20" },
  blue: { bg: "bg-accent", text: "text-accent", glow: "border-glow-accent", ring: "ring-accent/20" },
  amber: { bg: "bg-warning", text: "text-warning", glow: "", ring: "ring-warning/20" },
  rose: { bg: "bg-destructive", text: "text-destructive", glow: "", ring: "ring-destructive/20" },
  stone: { bg: "bg-muted-foreground", text: "text-muted-foreground", glow: "", ring: "ring-muted-foreground/20" },
  violet: { bg: "bg-accent", text: "text-accent", glow: "border-glow-accent", ring: "ring-accent/20" },
};

export function AgentCard({
  config,
  status,
  delay = 0,
}: {
  config: AgentConfig;
  status: AgentStatus;
  delay?: number;
}) {
  const Icon = config.icon;
  const colors = colorMap[config.color];

  return (
    <div
      className={cn(
        "glass-card rounded-2xl p-5 transition-all duration-500",
        status === "pending" && "opacity-40 scale-95",
        status === "active" && "opacity-100 scale-100 shadow-lg",
        status === "done" && cn("opacity-100 scale-100", colors.glow)
      )}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="flex items-center gap-3">
        {/* Icon with pulse */}
        <div className="relative shrink-0">
          <div
            className={cn(
              "flex h-12 w-12 items-center justify-center rounded-2xl transition-all",
              status === "pending" && "bg-secondary text-muted-foreground",
              status === "active" && cn(colors.bg, "text-white animate-pulse-glow"),
              status === "done" && cn(colors.bg, "text-white")
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
          {status === "active" && (
            <div className={cn("absolute -inset-1 rounded-2xl animate-ping", colors.ring)} />
          )}
        </div>

        {/* Label + status */}
        <div className="flex-1 min-w-0">
          <h4 className="font-display text-sm font-bold tracking-tight">{config.label}</h4>
          <p
            className={cn(
              "text-xs mt-0.5 transition-all",
              status === "done" ? "text-primary font-semibold" : "text-muted-foreground"
            )}
          >
            {status === "done" ? "Analysis complete" : config.statusText}
          </p>
        </div>

        {/* Status indicator */}
        <div className="shrink-0">
          {status === "pending" && (
            <div className="h-6 w-6 rounded-full border-2 border-border" />
          )}
          {status === "active" && (
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          )}
          {status === "done" && (
            <div className={cn("flex h-6 w-6 items-center justify-center rounded-full", colors.bg, "text-white")}>
              <Check className="h-4 w-4" />
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-1 rounded-full bg-secondary overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-700",
            status === "pending" && "w-0 bg-muted-foreground",
            status === "active" && "w-2/3 animate-pulse",
            status === "done" && cn("w-full", colors.bg)
          )}
        />
      </div>
    </div>
  );
}
