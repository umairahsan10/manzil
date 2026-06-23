"use client";

import { MapPin, Shield, Sun, Wallet } from "lucide-react";

/**
 * Floating glass trip card shown in the hero.
 * Static demo data: Karachi → Naran → Hunza
 */
export function FloatingTripCard() {
  return (
    <div className="relative animate-float-soft">
      {/* Glow */}
      <div className="absolute -inset-4 rounded-[2rem] bg-primary/10 blur-2xl" />

      {/* Card */}
      <div className="relative glass-strong rounded-[2rem] p-6 shadow-2xl w-[340px]">
        {/* Route */}
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <MapPin className="h-4 w-4" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Smart Trip</p>
            <h3 className="font-display text-base font-bold">Karachi → Naran → Hunza</h3>
          </div>
        </div>

        {/* Animated route line */}
        <div className="relative h-12 mb-4">
          <svg width="100%" height="48" viewBox="0 0 300 48" fill="none">
            <path
              d="M 20 24 Q 90 8, 150 24 T 280 24"
              stroke="url(#cardRoute)"
              strokeWidth="2.5"
              strokeLinecap="round"
              className="animate-route-draw"
            />
            <circle cx="20" cy="24" r="5" fill="#15803D" />
            <circle cx="150" cy="24" r="4" fill="#FFFFFF" stroke="#15803D" strokeWidth="2" />
            <circle cx="280" cy="24" r="5" fill="#2563EB" />
            <defs>
              <linearGradient id="cardRoute" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#15803D" />
                <stop offset="100%" stopColor="#2563EB" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          <Stat icon={Wallet} label="Budget" value="48.5k" />
          <Stat icon={Shield} label="Safety" value="91%" color="text-primary" />
          <Stat icon={Sun} label="Weather" value="Excellent" color="text-accent" />
        </div>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl bg-white/50 p-3 text-center">
      <Icon className={`h-4 w-4 mx-auto text-muted-foreground ${color || ""}`} />
      <p className={`text-sm font-bold mt-1 ${color || ""}`}>{value}</p>
      <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
    </div>
  );
}
