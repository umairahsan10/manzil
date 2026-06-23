"use client";

import { useState, useEffect, useRef } from "react";
import { Sparkles, Loader2, MapPin, Shield, Sun, Wallet, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { previewTrip } from "@/lib/api";
import type { UserQuery, PreviewResponse } from "@/lib/types";
import { getRouteStops, getDestinationShortName } from "@/lib/destinations";
import { RouteMap } from "@/components/route-map";

interface LivePreviewProps {
  query: UserQuery;
}

export function LivePreview({ query }: LivePreviewProps) {
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const result = await previewTrip(query);
        setPreview(result);
      } catch {
        setPreview(null);
      } finally {
        setLoading(false);
      }
    }, 800);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const top = preview?.top;
  const scores = preview?.rough_scores;
  const stops =
    top?.destinations
      ? getRouteStops(top.destinations)
      : [];

  return (
    <div className="glass-strong rounded-3xl overflow-hidden sticky top-40 shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b border-border/60 bg-white/40">
        <div className="relative">
          <Sparkles className={cn("h-5 w-5 text-primary", loading && "animate-pulse")} />
          {!loading && (
            <div className="absolute -inset-1 rounded-full bg-primary/20 animate-ping" />
          )}
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Current Best Match
          </p>
          <h3 className="font-display text-lg font-bold tracking-tight">
            {top?.label ?? "Analyzing..."}
          </h3>
        </div>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground ml-auto" />}
      </div>

      {/* Mini map */}
      <div className="relative h-[200px] bg-secondary">
        {stops.length > 0 ? (
          <RouteMap stops={stops} height="200px" className="rounded-none border-none" animated />
        ) : (
          <div className="flex items-center justify-center h-full">
            <MapPin className="h-8 w-8 text-muted-foreground/30" />
          </div>
        )}
      </div>

      {/* Route preview */}
      {top && stops.length > 0 && (
        <div className="px-6 py-4">
          <div className="flex items-center flex-wrap gap-1.5">
            {stops.map((stop, idx) => (
              <div key={stop.id} className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-foreground">
                  {getDestinationShortName(stop.id)}
                </span>
                {idx < stops.length - 1 && (
                  <span className="text-muted-foreground/50">→</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scores */}
      <div className="px-6 pb-6 space-y-3">
        {scores ? (
          <>
            <ScoreRow icon={Wallet} label="Budget fit" value={scores.budget_fit} color="primary" />
            <ScoreRow icon={Shield} label="Safety" value={scores.safety} color="primary" />
            <ScoreRow icon={Sun} label="Weather" value={scores.weather} color="accent" />
            <div className="h-px bg-border/60 my-3" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                <span className="text-sm font-bold">Trip Score</span>
              </div>
              <span className="text-2xl font-display font-bold text-primary">
                {Math.round(scores.trip_score * 100)}%
              </span>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center py-6 text-center">
            <p className="text-sm text-muted-foreground">
              {loading ? "Calculating..." : "Adjust your inputs to see a live preview"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreRow({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: "primary" | "accent";
}) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-3">
      <Icon className={cn("h-4 w-4", color === "primary" ? "text-primary" : "text-accent")} />
      <span className="text-sm font-medium text-muted-foreground flex-1">{label}</span>
      <div className="flex items-center gap-2 w-28">
        <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              color === "primary" ? "bg-primary" : "bg-accent"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs font-bold text-foreground w-8 text-right">{pct}%</span>
      </div>
    </div>
  );
}
