"use client";

import { ArrowRight, MapPin, Wallet, Shield, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { SAMPLE_TRIPS } from "@/lib/sample-trips";
import type { UserQuery } from "@/lib/types";
import { setPendingPlan } from "@/lib/storage";

interface SampleTripsModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (query: UserQuery) => void;
}

export function SampleTripsModal({ open, onClose, onSelect }: SampleTripsModalProps) {
  if (!open) return null;

  const handleSelect = (query: UserQuery) => {
    setPendingPlan(query);
    onSelect(query);
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-reveal-fade"
      onClick={onClose}
    >
      <div
        className="glass-strong rounded-3xl p-6 max-w-4xl w-full max-h-[85vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display text-2xl font-bold">Sample Trips</h2>
            <p className="text-sm text-muted-foreground mt-1">Pre-built plans to inspire your journey</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-xl">✕</button>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {SAMPLE_TRIPS.map((trip) => (
            <button
              key={trip.id}
              onClick={() => handleSelect(trip.query)}
              className="glass-card rounded-2xl p-5 text-left hover:shadow-lg hover:scale-[1.02] transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-display text-lg font-bold">{trip.name}</h3>
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                    <MapPin className="h-3 w-3" /> {trip.route}
                  </p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>

              <div className="grid grid-cols-3 gap-2 mb-3">
                <MiniStat icon={Wallet} label="Budget" value={`${(trip.budget / 1000).toFixed(0)}k`} />
                <MiniStat icon={Shield} label="Safety" value={`${trip.safety}%`} color="text-primary" />
                <MiniStat icon={Sun} label="Weather" value={trip.weather} color="text-accent" />
              </div>

              <div className="flex flex-wrap gap-1.5">
                {trip.badges.map((badge) => (
                  <span key={badge} className="rounded-full bg-secondary px-2.5 py-1 text-[10px] font-bold">
                    {badge}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MiniStat({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl bg-secondary/60 p-2 text-center">
      <Icon className={cn("h-3.5 w-3.5 mx-auto text-muted-foreground", color)} />
      <p className={cn("text-xs font-bold mt-1", color)}>{value}</p>
      <p className="text-[8px] font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
    </div>
  );
}
