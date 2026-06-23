"use client";

import { Car, Plane, Compass } from "lucide-react";
import { cn } from "@/lib/utils";
import { INTENSITY_LEVELS } from "@/lib/types";
import type { UserQuery, TravelMode } from "@/lib/types";

interface ExperiencePreferencesProps {
  query: UserQuery;
  updateQuery: <K extends keyof UserQuery>(key: K, value: UserQuery[K]) => void;
  toggleStyle: (tag: string) => void;
}

const styleChips: { value: string; label: string; icon: string }[] = [
  { value: "adventure", label: "Adventure", icon: "🏔️" },
  { value: "photography", label: "Photography", icon: "📸" },
  { value: "luxury", label: "Luxury", icon: "✨" },
  { value: "cultural", label: "Culture", icon: "🏛️" },
  { value: "relaxing", label: "Relaxation", icon: "🌿" },
  { value: "scenic", label: "Scenic", icon: "🌄" },
  { value: "food", label: "Food", icon: "🍲" },
  { value: "trekking", label: "Trekking", icon: "🥾" },
];

const travelModeCards: { value: TravelMode; label: string; icon: React.ElementType }[] = [
  { value: "road", label: "Road", icon: Car },
  { value: "air", label: "Flight", icon: Plane },
  { value: "hybrid", label: "Mixed", icon: Compass },
];

export function ExperiencePreferences({ query, updateQuery, toggleStyle }: ExperiencePreferencesProps) {
  return (
    <div className="space-y-6">
      {/* Travel style chips */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 block">
          Travel style
        </label>
        <div className="flex flex-wrap gap-2">
          {styleChips.map((chip) => {
            const isSelected = query.style_tags.includes(chip.value);
            return (
              <button
                key={chip.value}
                onClick={() => toggleStyle(chip.value)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-4 py-2.5 text-sm font-bold transition-all",
                  isSelected
                    ? "bg-primary text-primary-foreground shadow-md scale-105"
                    : "bg-secondary text-foreground hover:bg-secondary/70 hover:scale-105"
                )}
              >
                <span className="text-base">{chip.icon}</span>
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Trip intensity spectrum slider */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Trip intensity
          </label>
          <span className="text-lg font-display font-bold text-foreground">
            {INTENSITY_LEVELS[query.difficulty_tolerance - 1]?.label ?? "Balanced"}
          </span>
        </div>
        <div className="relative">
          {/* Track */}
          <div className="relative h-4 rounded-full bg-secondary overflow-hidden">
            <div
              className="absolute inset-0 opacity-20"
              style={{
                background: "linear-gradient(to right, #15803D, #2563EB, #D97706, #DC2626)",
              }}
            />
          </div>
          {/* Stop labels */}
          <div className="flex justify-between mt-3">
            {INTENSITY_LEVELS.map((level) => {
              const isSelected = query.difficulty_tolerance === level.value;
              return (
                <button
                  key={level.value}
                  onClick={() => updateQuery("difficulty_tolerance", level.value)}
                  className={cn(
                    "flex flex-col items-center gap-1 transition-all",
                    isSelected ? "scale-110" : "opacity-50 hover:opacity-100"
                  )}
                >
                  <div
                    className={cn(
                      "h-3 w-3 rounded-full transition-all",
                      isSelected
                        ? "bg-primary shadow-md ring-4 ring-primary/20"
                        : "bg-muted-foreground/40"
                    )}
                  />
                  <span
                    className={cn(
                      "text-[10px] font-bold uppercase tracking-widest",
                      isSelected ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {level.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Travel mode cards */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 block">
          Travel mode
        </label>
        <div className="grid grid-cols-3 gap-3">
          {travelModeCards.map((mode) => {
            const Icon = mode.icon;
            const isSelected = query.travel_mode_pref === mode.value;
            return (
              <button
                key={mode.value}
                onClick={() => updateQuery("travel_mode_pref", mode.value)}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-2xl p-4 transition-all",
                  isSelected
                    ? "bg-accent text-accent-foreground shadow-lg border-glow-accent"
                    : "bg-secondary text-foreground hover:bg-secondary/70 border border-border"
                )}
              >
                <Icon className="h-6 w-6" />
                <span className="text-sm font-bold">{mode.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
