"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Shield, Sun, MapPin, Car, Plane, CircleDot,
  ChevronDown, Bookmark, Share2, Edit, AlertTriangle, Hospital, Phone,
  Mountain, Camera, Utensils, Sunrise, Trophy, Clock
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getPendingPlan, saveTrip, isTripSaved, shareTrip } from "@/lib/storage";
import type { PlanResponse, RouteCandidate, UserQuery, DayPlan, DebateResult } from "@/lib/types";
import { getRouteStops, deriveTripName } from "@/lib/destinations";
import { RouteMap } from "@/components/route-map";

export default function TripDetailPage() {
  const params = useParams();
  const router = useRouter();
  const candidateId = params.id as string;
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [query, setQuery] = useState<UserQuery | null>(null);
  const [candidate, setCandidate] = useState<RouteCandidate | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const pending = getPendingPlan();
    if (!pending?.response) {
      router.push("/plan");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlan(pending.response);
    setQuery(pending.query);
    const c = pending.response.candidates.find((c) => c.candidate_id === candidateId);
    if (!c) {
      router.push("/results");
      return;
    }
    setCandidate(c);
    setSaved(isTripSaved(c.candidate_id));
  }, [candidateId, router]);

  if (!plan || !query || !candidate) return null;

  const debate = plan.debate_result;
  const stops = getRouteStops(candidate.destinations);
  const fullPlan = debate?.full_plan;
  const days = fullPlan?.days || [];
  const tripName = deriveTripName(candidate);
  const cost = candidate.estimated_cost ?? candidate.total_cost_pkr ?? 0;

  const handleSave = () => {
    if (saved) return;
    saveTrip(plan.trip_id, candidate, query, plan);
    setSaved(true);
  };

  const handleShare = async () => {
    await shareTrip(plan.trip_id, candidate.candidate_id, query, tripName);
  };

  return (
    <div className="min-h-screen bg-background pt-20 pb-24">
      <div className="container">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push("/results")}
            className="text-sm font-semibold text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-1"
          >
            ← Back to results
          </button>
          <div className="flex items-center gap-3">
            {candidate.candidate_id === debate?.debate_trace?.orchestrator?.final_winner_id && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-bold text-primary-foreground">
                <Trophy className="h-3 w-3" /> Recommended
              </span>
            )}
            <h1 className="text-3xl font-display font-bold tracking-tight sm:text-4xl">{tripName}</h1>
          </div>
        </div>

        {/* Top: interactive map */}
        {stops.length > 0 && (
          <div className="mb-8 glass-card rounded-3xl overflow-hidden">
            <div className="h-[400px]">
              <RouteMap stops={stops} height="100%" className="rounded-none border-none" animated />
            </div>
          </div>
        )}

        {/* Day-by-day timeline */}
        {days.length > 0 && (
          <Section title="Day-by-Day Timeline" subtitle="Your full itinerary">
            <div className="relative">
              <div className="absolute left-6 top-4 bottom-4 w-px bg-border" />
              <div className="space-y-4">
                {days.map((day, idx) => (
                  <DayCard key={idx} day={day} index={idx} />
                ))}
              </div>
            </div>
          </Section>
        )}

        {/* Budget breakdown */}
        {debate?.cost_breakdown && (
          <Section title="Budget Breakdown" subtitle="Where your money goes" defaultOpen={false}>
            <BudgetBreakdown breakdown={debate.cost_breakdown} />
          </Section>
        )}

        {/* Safety analysis */}
        {debate?.safety_analysis && (
          <Section title="Safety Analysis" subtitle="Altitude, roads, and emergency info" defaultOpen={false}>
            <SafetyAnalysisSection analysis={debate.safety_analysis} />
          </Section>
        )}

        {/* Weather overview */}
        {days.some((d) => d.weather) && (
          <Section title="Weather Overview" subtitle="Daily forecasts for your trip" defaultOpen={false}>
            <WeatherOverview days={days} />
          </Section>
        )}

        {/* Experience layer */}
        {debate?.experience_layer && (
          <Section title="Experience Layer" subtitle="Hidden spots, local foods, photo points" defaultOpen={false}>
            <ExperienceLayerSection layer={debate.experience_layer} />
          </Section>
        )}

        {/* Alternative routes */}
        {debate?.why_not && Object.keys(debate.why_not).length > 0 && (
          <Section title="Alternative Routes" subtitle="Why not these?" defaultOpen={false}>
            <div className="space-y-3">
              {Object.entries(debate.why_not).map(([id, reason]) => (
                <div key={id} className="glass-card rounded-2xl p-4">
                  <p className="font-bold text-sm mb-1">{id}</p>
                  <p className="text-sm text-muted-foreground">{reason}</p>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>

      {/* Sticky bottom CTA */}
      <div className="fixed bottom-0 left-0 right-0 z-40 glass-strong border-t border-border/60 px-4 py-3">
        <div className="container flex items-center justify-between gap-3">
          <div className="hidden sm:block">
            <p className="font-display font-bold">{tripName}</p>
            <p className="text-xs text-muted-foreground">PKR {cost.toLocaleString()} · {candidate.days} days</p>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => router.push("/plan")}
              className="rounded-xl bg-secondary text-foreground px-4 py-2.5 text-sm font-bold hover:bg-secondary/70 transition-all inline-flex items-center gap-2"
            >
              <Edit className="h-4 w-4" /> Edit
            </button>
            <button
              onClick={handleShare}
              className="rounded-xl bg-secondary text-foreground px-4 py-2.5 text-sm font-bold hover:bg-secondary/70 transition-all inline-flex items-center gap-2"
            >
              <Share2 className="h-4 w-4" /> Share
            </button>
            <button
              onClick={handleSave}
              disabled={saved}
              className={cn(
                "rounded-xl px-5 py-2.5 text-sm font-bold transition-all inline-flex items-center gap-2",
                saved
                  ? "bg-primary/20 text-primary cursor-default"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              )}
            >
              <Bookmark className="h-4 w-4" /> {saved ? "Saved" : "Save Trip"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  subtitle,
  defaultOpen = true,
  children,
}: {
  title: string;
  subtitle: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-6 glass-card rounded-3xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-white/30 transition-colors"
      >
        <div>
          <h3 className="font-display text-lg font-bold">{title}</h3>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <ChevronDown className={cn("h-5 w-5 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      <div className={cn("grid transition-all duration-300", open ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}>
        <div className="overflow-hidden">
          <div className="px-5 pb-5 pt-2">
            <div className="h-px bg-border/60 mb-4" />
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

function DayCard({ day, index }: { day: DayPlan; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const stop = day.stops[0];
  const modeIcon = day.travel_mode === "air" ? Plane : day.travel_mode === "hybrid" ? CircleDot : Car;
  const ModeIcon = modeIcon;
  const weather = day.weather;
  const roadRisk = day.road_risk;

  return (
    <div className="relative flex gap-4">
      <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold shadow-md">
        {day.day_index || index + 1}
      </div>
      <div
        className="flex-1 glass-card rounded-2xl p-4 cursor-pointer hover:shadow-md transition-all"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h4 className="font-display text-base font-bold">{stop?.name || `Day ${day.day_index}`}</h4>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
              {day.drive_time_hours != null && (
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {day.drive_time_hours}h drive
                </span>
              )}
              {day.travel_mode && (
                <span className="inline-flex items-center gap-1">
                  <ModeIcon className="h-3 w-3" /> {day.travel_mode}
                </span>
              )}
              {day.stay_type && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> {day.stay_type}
                </span>
              )}
              {day.altitude_m != null && (
                <span className="inline-flex items-center gap-1">
                  <Mountain className="h-3 w-3" /> {day.altitude_m}m
                </span>
              )}
            </div>
          </div>
          <div className="text-right shrink-0">
            {day.estimated_cost != null && (
              <p className="text-sm font-bold">PKR {day.estimated_cost.toLocaleString()}</p>
            )}
            {weather && (
              <p className={cn("text-xs font-semibold", weatherColor(weather.condition))}>
                {weather.condition}
              </p>
            )}
          </div>
        </div>

        {expanded && (
          <div className="mt-4 space-y-3 animate-reveal-fade">
            {day.weather_note && <NoteRow icon={Sun} label="Weather" text={day.weather_note} color="text-accent" />}
            {day.road_note && <NoteRow icon={Car} label="Road" text={day.road_note} color="text-warning" />}
            {day.safety_note && <NoteRow icon={Shield} label="Safety" text={day.safety_note} color="text-destructive" />}
            {weather && (
              <div className="flex items-center gap-4 rounded-xl bg-secondary/50 p-3">
                <Sun className="h-5 w-5 text-accent" />
                <div className="flex-1">
                  <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Weather</p>
                  <p className="text-sm font-semibold">
                    {weather.temp_high_c != null && weather.temp_low_c != null
                      ? `${weather.temp_high_c}° / ${weather.temp_low_c}°`
                      : weather.summary || "—"}
                  </p>
                </div>
                {weather.precip_prob_pct != null && (
                  <span className="text-xs font-bold text-accent">{weather.precip_prob_pct}% rain</span>
                )}
              </div>
            )}
            {roadRisk && roadRisk.risk_level !== "low" && (
              <div className={cn(
                "flex items-center gap-2 rounded-xl p-3",
                roadRisk.risk_level === "high" ? "bg-destructive/5" : "bg-warning/5"
              )}>
                <AlertTriangle className={cn("h-4 w-4", roadRisk.risk_level === "high" ? "text-destructive" : "text-warning")} />
                <span className="text-sm font-semibold">{roadRisk.segment}: {roadRisk.risk_level} risk</span>
              </div>
            )}
            {stop?.activities && stop.activities.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Activities</p>
                <div className="flex flex-wrap gap-2">
                  {stop.activities.map((a) => (
                    <span key={a} className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold">{a}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function NoteRow({ icon: Icon, label, text, color }: { icon: React.ElementType; label: string; text: string; color: string }) {
  return (
    <div className="flex items-start gap-2">
      <Icon className={cn("h-4 w-4 shrink-0 mt-0.5", color)} />
      <div>
        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}: </span>
        <span className="text-sm">{text}</span>
      </div>
    </div>
  );
}

function BudgetBreakdown({ breakdown }: { breakdown: NonNullable<DebateResult["cost_breakdown"]> }) {
  const items = [
    { label: "Transport", value: breakdown.transport, icon: Car },
    { label: "Hotels", value: breakdown.lodging, icon: MapPin },
    { label: "Food", value: breakdown.food, icon: Utensils },
    { label: "Activities", value: breakdown.activities, icon: Camera },
    { label: "Emergency Buffer", value: breakdown.buffer, icon: Shield },
  ];
  const total = breakdown.total || items.reduce((s, i) => s + i.value, 0);

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const pct = total > 0 ? (item.value / total) * 100 : 0;
        const Icon = item.icon;
        return (
          <div key={item.label}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-semibold">{item.label}</span>
              </div>
              <span className="text-sm font-bold">PKR {item.value.toLocaleString()}</span>
            </div>
            <div className="h-2 rounded-full bg-secondary overflow-hidden">
              <div className="h-full grad-primary rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
      <div className="flex items-center justify-between pt-3 border-t border-border/60">
        <span className="font-display font-bold text-lg">Total</span>
        <span className="font-display font-bold text-lg text-primary">PKR {total.toLocaleString()}</span>
      </div>
    </div>
  );
}

function SafetyAnalysisSection({ analysis }: { analysis: NonNullable<DebateResult["safety_analysis"]> }) {
  return (
    <div className="space-y-6">
      {/* Altitude progression chart */}
      {analysis.altitude_progression.length > 0 && (
        <div>
          <h4 className="text-sm font-bold mb-3">Altitude Progression</h4>
          <AltitudeChart points={analysis.altitude_progression} threshold={analysis.applied_threshold_m} />
        </div>
      )}

      {/* Road risk cards */}
      {analysis.road_risk_cards.length > 0 && (
        <div>
          <h4 className="text-sm font-bold mb-3">Road Risk</h4>
          <div className="space-y-2">
            {analysis.road_risk_cards.map((card, idx) => (
              <div key={idx} className={cn(
                "flex items-center gap-3 rounded-xl p-3",
                card.risk_level === "high" ? "bg-destructive/5" : card.risk_level === "moderate" ? "bg-warning/5" : "bg-secondary/50"
              )}>
                <AlertTriangle className={cn(
                  "h-4 w-4",
                  card.risk_level === "high" ? "text-destructive" : card.risk_level === "moderate" ? "text-warning" : "text-muted-foreground"
                )} />
                <span className="text-sm font-semibold flex-1">{card.segment}</span>
                <span className="text-xs font-bold uppercase">{card.risk_level}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hospital proximity */}
      {analysis.hospital_proximity.length > 0 && (
        <div>
          <h4 className="text-sm font-bold mb-3">Hospital Proximity</h4>
          <div className="grid sm:grid-cols-2 gap-2">
            {analysis.hospital_proximity.map((h, idx) => (
              <div key={idx} className="flex items-center gap-2 rounded-xl bg-secondary/50 p-3">
                <Hospital className="h-4 w-4 text-primary" />
                <div className="flex-1">
                  <p className="text-sm font-semibold">{h.name}</p>
                  <p className="text-xs text-muted-foreground">{h.distance_km} km · {h.level}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Emergency contacts */}
      {analysis.emergency_contacts.length > 0 && (
        <div>
          <h4 className="text-sm font-bold mb-3">Emergency Contacts</h4>
          <div className="flex flex-wrap gap-3">
            {analysis.emergency_contacts.map((c, idx) => (
              <div key={idx} className="flex items-center gap-2 rounded-xl bg-secondary/50 p-3">
                <Phone className="h-4 w-4 text-destructive" />
                <div>
                  <p className="text-xs font-bold">{c.label}</p>
                  <p className="text-sm font-semibold">{c.number}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AltitudeChart({ points, threshold }: { points: Array<{ day: number; destination_name: string; altitude_m: number }>; threshold: number }) {
  const maxAlt = Math.max(...points.map((p) => p.altitude_m), threshold);
  const chartHeight = 120;

  return (
    <div className="relative">
      <svg width="100%" height={chartHeight + 30} viewBox={`0 0 ${points.length * 80} ${chartHeight + 30}`}>
        {/* Threshold line */}
        {threshold > 0 && (
          <line
            x1="0" y1={chartHeight - (threshold / maxAlt) * chartHeight}
            x2={points.length * 80} y2={chartHeight - (threshold / maxAlt) * chartHeight}
            stroke="#DC2626" strokeWidth="1" strokeDasharray="4 4" opacity="0.5"
          />
        )}
        {/* Altitude area */}
        <path
          d={points.map((p, i) => {
            const x = i * 80 + 40;
            const y = chartHeight - (p.altitude_m / maxAlt) * chartHeight;
            return `${i === 0 ? "M" : "L"} ${x} ${y}`;
          }).join(" ") + ` L ${points.length * 80 - 40} ${chartHeight} L 40 ${chartHeight} Z`}
          fill="url(#altGrad)" opacity="0.3"
        />
        {/* Altitude line */}
        <path
          d={points.map((p, i) => {
            const x = i * 80 + 40;
            const y = chartHeight - (p.altitude_m / maxAlt) * chartHeight;
            return `${i === 0 ? "M" : "L"} ${x} ${y}`;
          }).join(" ")}
          fill="none" stroke="#15803D" strokeWidth="2"
        />
        {/* Points */}
        {points.map((p, i) => {
          const x = i * 80 + 40;
          const y = chartHeight - (p.altitude_m / maxAlt) * chartHeight;
          return (
            <g key={i}>
              <circle cx={x} cy={y} r="4" fill="#15803D" />
              <text x={x} y={chartHeight + 20} textAnchor="middle" fontSize="10" fill="#6B7280" fontWeight="bold">
                {p.destination_name.split(",")[0].slice(0, 8)}
              </text>
              <text x={x} y={y - 8} textAnchor="middle" fontSize="9" fill="#1A1A1A" fontWeight="bold">
                {p.altitude_m}m
              </text>
            </g>
          );
        })}
        <defs>
          <linearGradient id="altGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#15803D" />
            <stop offset="100%" stopColor="#15803D" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

function WeatherOverview({ days }: { days: DayPlan[] }) {
  const weatherDays = days.filter((d) => d.weather);
  if (weatherDays.length === 0) return null;

  return (
    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
      {weatherDays.map((day, idx) => {
        const w = day.weather!;
        return (
          <div key={idx} className="flex-shrink-0 w-32 glass-card rounded-2xl p-4 text-center">
            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Day {day.day_index}</p>
            <Sun className={cn("h-6 w-6 mx-auto my-2", weatherColor(w.condition))} />
            <p className="text-sm font-bold">{w.condition}</p>
            {w.temp_high_c != null && w.temp_low_c != null && (
              <p className="text-xs text-muted-foreground mt-1">{w.temp_high_c}° / {w.temp_low_c}°</p>
            )}
            {w.precip_prob_pct != null && (
              <p className="text-xs font-semibold text-accent mt-1">{w.precip_prob_pct}% rain</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ExperienceLayerSection({ layer }: { layer: NonNullable<DebateResult["experience_layer"]> }) {
  const sections = [
    { title: "Hidden Spots", items: layer.hidden_spots, icon: MapPin, color: "text-accent" },
    { title: "Local Foods", items: layer.local_foods, icon: Utensils, color: "text-warning" },
    { title: "Sunrise Points", items: layer.sunrise_points, icon: Sunrise, color: "text-primary" },
    { title: "Photo Spots", items: layer.photo_spots, icon: Camera, color: "text-accent" },
  ];

  return (
    <div className="grid sm:grid-cols-2 gap-4">
      {sections.map((section) => {
        if (section.items.length === 0) return null;
        const Icon = section.icon;
        return (
          <div key={section.title}>
            <h4 className="flex items-center gap-2 text-sm font-bold mb-3">
              <Icon className={cn("h-4 w-4", section.color)} /> {section.title}
            </h4>
            <div className="space-y-2">
              {section.items.slice(0, 5).map((spot, idx) => (
                <div key={idx} className="rounded-xl bg-secondary/50 p-3">
                  <p className="text-sm font-semibold">{spot.name}</p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{spot.description}</p>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function weatherColor(condition: string): string {
  if (condition === "Excellent") return "text-primary";
  if (condition === "Good") return "text-accent";
  if (condition === "Fair") return "text-warning";
  return "text-destructive";
}
