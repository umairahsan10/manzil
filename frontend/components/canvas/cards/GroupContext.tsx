"use client";

import { Users, Heart, PersonStanding, Sparkles, Car, Mountain, Baby } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserQuery, GroupType } from "@/lib/types";

interface GroupContextProps {
  query: UserQuery;
  updateQuery: <K extends keyof UserQuery>(key: K, value: UserQuery[K]) => void;
}

const groupCards: { value: GroupType; label: string; icon: React.ElementType }[] = [
  { value: "friends", label: "Friends", icon: Users },
  { value: "family", label: "Family", icon: Heart },
  { value: "couple", label: "Couple", icon: Sparkles },
  { value: "solo", label: "Solo", icon: PersonStanding },
  { value: "mixed", label: "Mixed", icon: Users },
];

const specialToggles: {
  key: keyof UserQuery;
  label: string;
  icon: React.ElementType;
  desc: string;
}[] = [
  { key: "kids_in_group", label: "Kids included", icon: Baby, desc: "Under 10 years" },
  { key: "altitude_sensitive", label: "Altitude sensitive", icon: Mountain, desc: "Lower altitude ceiling" },
  { key: "luxury_stays_needed", label: "Luxury stays needed", icon: Sparkles, desc: "Premium hotels" },
  { key: "motion_sickness", label: "Motion sickness", icon: Car, desc: "Avoid winding passes" },
  { key: "road_trip_only", label: "Road trip only", icon: Car, desc: "No flights" },
];

export function GroupContext({ query, updateQuery }: GroupContextProps) {
  return (
    <div className="space-y-6">
      {/* Group type cards */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 block">
          Group type
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {groupCards.map((card) => {
            const Icon = card.icon;
            const isSelected = query.group_composition === card.value;
            return (
              <button
                key={card.value}
                onClick={() => updateQuery("group_composition", card.value)}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-2xl p-4 transition-all",
                  isSelected
                    ? "bg-primary text-primary-foreground shadow-lg border-glow"
                    : "bg-secondary text-foreground hover:bg-secondary/70 border border-border"
                )}
              >
                <Icon className="h-6 w-6" />
                <span className="text-sm font-bold">{card.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Group size */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Group size
          </label>
          <span className="text-2xl font-display font-bold text-foreground">
            {query.group_size} {query.group_size === 1 ? "person" : "people"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => updateQuery("group_size", Math.max(1, query.group_size - 1))}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-foreground font-bold hover:bg-secondary/70 transition-all"
          >
            −
          </button>
          <div className="flex-1 h-2 rounded-full bg-secondary relative overflow-hidden">
            <div
              className="absolute left-0 top-0 h-full grad-primary rounded-full transition-all duration-300"
              style={{ width: `${(query.group_size / 20) * 100}%` }}
            />
          </div>
          <button
            onClick={() => updateQuery("group_size", Math.min(20, query.group_size + 1))}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-foreground font-bold hover:bg-secondary/70 transition-all"
          >
            +
          </button>
        </div>
      </div>

      {/* Elders toggle (visually grouped with special conditions) */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 block">
          Special conditions
        </label>
        <div className="space-y-2">
          <ToggleRow
            icon={PersonStanding}
            label="Elders in group"
            desc="Over 60 years"
            checked={query.elderly_in_group}
            onCheckedChange={(c) => updateQuery("elderly_in_group", c)}
          />
          {specialToggles.map((toggle) => {
            const Icon = toggle.icon;
            return (
              <ToggleRow
                key={toggle.key}
                icon={Icon}
                label={toggle.label}
                desc={toggle.desc}
                checked={query[toggle.key] as boolean}
                onCheckedChange={(c) => updateQuery(toggle.key, c as UserQuery[keyof UserQuery])}
              />
            );
          })}
        </div>
      </div>

      {/* Foreign traveller */}
      <div>
        <ToggleRow
          icon={Sparkles}
          label="Foreign traveller"
          desc="NOC permits considered"
          checked={query.is_foreign_traveller}
          onCheckedChange={(c) => updateQuery("is_foreign_traveller", c)}
        />
      </div>
    </div>
  );
}

function ToggleRow({
  icon: Icon,
  label,
  desc,
  checked,
  onCheckedChange,
}: {
  icon: React.ElementType;
  label: string;
  desc: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <button
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "w-full flex items-center gap-3 rounded-2xl p-4 transition-all border",
        checked
          ? "bg-primary/5 border-primary/30"
          : "bg-secondary/50 border-border hover:bg-secondary"
      )}
    >
      <div
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-xl transition-all shrink-0",
          checked ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground"
        )}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 text-left">
        <p className={cn("text-sm font-bold", checked && "text-primary")}>{label}</p>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
      <div
        className={cn(
          "h-6 w-11 rounded-full transition-all relative shrink-0",
          checked ? "bg-primary" : "bg-border"
        )}
      >
        <div
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-all",
            checked ? "left-[22px]" : "left-0.5"
          )}
        />
      </div>
    </button>
  );
}
