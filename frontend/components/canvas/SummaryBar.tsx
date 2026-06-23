"use client";

import { useState, useRef, useEffect } from "react";
import { MapPin, Wallet, Calendar, Users, Gauge, Sparkles, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { INTENSITY_LEVELS, ORIGIN_CITIES, GROUP_TYPES } from "@/lib/types";
import type { UserQuery } from "@/lib/types";

interface SummaryBarProps {
  query: UserQuery;
  updateQuery: <K extends keyof UserQuery>(key: K, value: UserQuery[K]) => void;
}

export function SummaryBar({ query, updateQuery }: SummaryBarProps) {
  return (
    <div className="sticky top-20 z-30 mt-4">
      <div className="glass-strong rounded-2xl px-4 py-3 shadow-lg">
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground shrink-0 mr-1">
            Trip
          </span>
          <Pill
            icon={MapPin}
            label="From"
            value={capitalize(query.origin_city)}
            options={ORIGIN_CITIES.map((c) => ({ value: c, label: capitalize(c) }))}
            onSelect={(v) => updateQuery("origin_city", v)}
          />
          <Pill
            icon={Wallet}
            label="Budget"
            value={`${(query.budget_pkr / 1000).toFixed(0)}k`}
            options={[
              { value: "50000", label: "50k" },
              { value: "100000", label: "100k" },
              { value: "150000", label: "150k" },
              { value: "200000", label: "200k" },
              { value: "300000", label: "300k" },
            ]}
            onSelect={(v) => updateQuery("budget_pkr", parseInt(v))}
          />
          <Pill
            icon={Calendar}
            label="Days"
            value={`${query.days}d`}
            options={[3, 5, 7, 10, 14].map((d) => ({ value: String(d), label: `${d} days` }))}
            onSelect={(v) => updateQuery("days", parseInt(v))}
          />
          <Pill
            icon={Users}
            label="Group"
            value={capitalize(query.group_composition)}
            options={GROUP_TYPES.map((g) => ({ value: g.value, label: g.label }))}
            onSelect={(v) => updateQuery("group_composition", v as UserQuery["group_composition"])}
          />
          <Pill
            icon={Gauge}
            label="Intensity"
            value={INTENSITY_LEVELS[query.difficulty_tolerance - 1]?.label ?? "Balanced"}
            options={INTENSITY_LEVELS.map((l) => ({ value: String(l.value), label: l.label }))}
            onSelect={(v) => updateQuery("difficulty_tolerance", parseInt(v))}
          />
          <Pill
            icon={Sparkles}
            label="Style"
            value={query.style_tags[0] ? capitalize(query.style_tags[0]) : "—"}
            options={[
              { value: "scenic", label: "Scenic" },
              { value: "adventure", label: "Adventure" },
              { value: "cultural", label: "Culture" },
              { value: "photography", label: "Photography" },
              { value: "relaxing", label: "Relaxation" },
              { value: "luxury", label: "Luxury" },
            ]}
            onSelect={(v) =>
              updateQuery("style_tags", query.style_tags.includes(v) ? query.style_tags : [v, ...query.style_tags].slice(0, 3))
            }
          />
        </div>
      </div>
    </div>
  );
}

function Pill({
  icon: Icon,
  label,
  value,
  options,
  onSelect,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onSelect: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all",
          open
            ? "bg-primary text-primary-foreground shadow-md"
            : "bg-secondary text-foreground hover:bg-secondary/70"
        )}
      >
        <Icon className="h-3 w-3" />
        <span className="text-muted-foreground/70 hidden sm:inline">{label}:</span>
        <span>{value}</span>
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-2 z-50 glass-strong rounded-xl shadow-xl p-1.5 min-w-[140px] animate-reveal-fade">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                onSelect(opt.value);
                setOpen(false);
              }}
              className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-foreground hover:bg-secondary transition-colors"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
