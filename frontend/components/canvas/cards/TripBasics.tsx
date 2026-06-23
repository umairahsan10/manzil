"use client";

import { MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { MONTHS, ORIGIN_CITIES } from "@/lib/types";
import type { UserQuery } from "@/lib/types";

interface TripBasicsProps {
  query: UserQuery;
  updateQuery: <K extends keyof UserQuery>(key: K, value: UserQuery[K]) => void;
}

export function TripBasics({ query, updateQuery }: TripBasicsProps) {
  const helperText = deriveHelper(query);

  return (
    <div className="space-y-6">
      {/* Origin city cards */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 block">
          Origin city
        </label>
        <div className="grid grid-cols-3 gap-3">
          {ORIGIN_CITIES.map((city) => (
            <button
              key={city}
              onClick={() => updateQuery("origin_city", city)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl p-4 transition-all",
                query.origin_city === city
                  ? "bg-primary text-primary-foreground shadow-lg border-glow"
                  : "bg-secondary text-foreground hover:bg-secondary/70 border border-border"
              )}
            >
              <MapPin className="h-5 w-5" />
              <span className="text-sm font-bold capitalize">{city}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Travel month */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 block">
          Travel month
        </label>
        <div className="flex flex-wrap gap-2">
          {MONTHS.map((month, idx) => {
            const monthNum = idx + 1;
            const isSelected = query.travel_month === monthNum;
            const isPeak = monthNum >= 5 && monthNum <= 10;
            return (
              <button
                key={month}
                onClick={() => updateQuery("travel_month", monthNum)}
                className={cn(
                  "rounded-xl px-3 py-2 text-xs font-semibold transition-all",
                  isSelected
                    ? "bg-accent text-accent-foreground shadow-md"
                    : isPeak
                      ? "bg-secondary text-foreground hover:bg-secondary/70"
                      : "bg-secondary/50 text-muted-foreground hover:bg-secondary"
                )}
              >
                {month.slice(0, 3)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Budget slider */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Budget
          </label>
          <span className="text-2xl font-display font-bold text-foreground">
            PKR {(query.budget_pkr / 1000).toFixed(0)}k
          </span>
        </div>
        <div className="relative">
          <input
            type="range"
            min={20000}
            max={1000000}
            step={10000}
            value={query.budget_pkr}
            onChange={(e) => updateQuery("budget_pkr", parseInt(e.target.value))}
            className="w-full h-3 rounded-full appearance-none cursor-pointer bg-secondary accent-primary"
            style={{
              background: `linear-gradient(to right, #15803D 0%, #15803D ${((query.budget_pkr - 20000) / 980000) * 100}%, #F3F1EC ${((query.budget_pkr - 20000) / 980000) * 100}%, #F3F1EC 100%)`,
            }}
          />
          <div className="flex justify-between mt-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            <span>20k</span>
            <span>500k</span>
            <span>1M</span>
          </div>
        </div>
      </div>

      {/* Days */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Number of days
          </label>
          <span className="text-2xl font-display font-bold text-foreground">{query.days}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => updateQuery("days", Math.max(2, query.days - 1))}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-foreground font-bold hover:bg-secondary/70 transition-all"
          >
            −
          </button>
          <div className="flex-1 h-2 rounded-full bg-secondary relative overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full grad-primary rounded-full transition-all duration-300"
              style={{ width: `${(query.days / 21) * 100}%` }}
            />
          </div>
          <button
            onClick={() => updateQuery("days", Math.min(21, query.days + 1))}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-foreground font-bold hover:bg-secondary/70 transition-all"
          >
            +
          </button>
        </div>
      </div>

      {/* Live helper */}
      <div className="flex items-center gap-2 rounded-2xl bg-accent/5 border border-accent/20 px-4 py-3">
        <SparkleIcon />
        <p className="text-sm font-medium text-accent">{helperText}</p>
      </div>
    </div>
  );
}

function deriveHelper(query: UserQuery): string {
  const month = query.travel_month;
  const budget = query.budget_pkr;
  if (month >= 6 && month <= 9 && budget >= 100000) return "Best for Hunza + Naran";
  if (month >= 5 && month <= 10 && budget >= 80000) return "Best for Swat + Naran";
  if (month >= 4 && month <= 10 && budget >= 150000) return "Best for Skardu + Deosai";
  if (budget < 50000) return "Best for Murree + Swat day trips";
  return "Best for Hunza + Naran";
}

function SparkleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-accent shrink-0">
      <path
        d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z"
        fill="currentColor"
      />
    </svg>
  );
}
