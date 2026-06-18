"use client";

import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import {
  Loader2,
  Sparkles,
  Users,
  Calendar,
  Wallet,
  Settings2,
  AlertCircle,
  MapPin,
  Brain,
  Compass,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { planTrip } from "@/lib/api";
import {
  GROUP_TYPES,
  MONTHS,
  ORIGIN_CITIES,
  STYLE_TAGS,
  TRAVEL_MODES,
  PlanResponse,
  UserQuery,
} from "@/lib/types";
import {
  RouteHero,
  CandidateSelector,
  AgentScorecard,
  DissentBox,
  WhyNotList,
  OrchestratorReasoning,
  DeveloperDetails,
  ItineraryPreview,
} from "@/components/plan-results";
import { getRouteStops } from "@/lib/destinations";

const defaultQuery: UserQuery = {
  group_size: 4,
  group_composition: "family",
  budget_pkr: 150000,
  days: 7,
  travel_month: 6,
  travel_mode_pref: "road",
  origin_city: "islamabad",
  style_tags: ["scenic", "cultural"],
  difficulty_tolerance: 3,
  is_foreign_traveller: false,
  elderly_in_group: false,
};

const presets: { label: string; emoji: string; query: UserQuery }[] = [
  {
    label: "Family Scenic",
    emoji: "👨‍👩‍👧‍👦",
    query: {
      ...defaultQuery,
      group_composition: "family",
      style_tags: ["scenic", "relaxing"],
      difficulty_tolerance: 2,
      elderly_in_group: true,
    },
  },
  {
    label: "Solo Adventure",
    emoji: "🎒",
    query: {
      ...defaultQuery,
      group_size: 1,
      group_composition: "solo",
      style_tags: ["adventure", "trekking"],
      difficulty_tolerance: 4,
      budget_pkr: 80000,
    },
  },
  {
    label: "Friends Road Trip",
    emoji: "🚗",
    query: {
      ...defaultQuery,
      group_size: 5,
      group_composition: "friends",
      style_tags: ["adventure", "food", "photography"],
      difficulty_tolerance: 3,
      budget_pkr: 120000,
    },
  },
];

function useReveal() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("visible");
          obs.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useReveal();
  return (
    <div
      ref={ref}
      className={`reveal ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

export default function PlanPage() {
  const [query, setQuery] = useState<UserQuery>(defaultQuery);
  const [fullLlmMode, setFullLlmMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanResponse | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (result && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  const updateQuery = <K extends keyof UserQuery>(
    key: K,
    value: UserQuery[K]
  ) => {
    setQuery((prev) => ({ ...prev, [key]: value }));
  };

  const toggleStyle = (tag: string) => {
    setQuery((prev) => ({
      ...prev,
      style_tags: prev.style_tags.includes(tag)
        ? prev.style_tags.filter((t) => t !== tag)
        : [...prev.style_tags, tag],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const response = await planTrip(query, fullLlmMode);
      setResult(response);
      localStorage.setItem("manzil:last-trip", JSON.stringify(response));
      toast.success("Trip planned successfully!");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to plan trip"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pt-24 pb-20">
      <div className="container">
        {/* Header */}
        <Reveal className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4">
            <Compass className="h-3.5 w-3.5 text-primary" />
            Plan your route
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
            Tell us what you want.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
            The agents will debate three routes and pick the one that fits your
            group, budget, and style.
          </p>
        </Reveal>

        {/* Form */}
        <Reveal delay={100}>
          <Card className="mx-auto max-w-3xl overflow-hidden rounded-[2.5rem] border-border shadow-xl shadow-primary/5">
            <CardHeader className="border-b border-border bg-secondary/30 px-8 py-6">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings2 className="h-5 w-5 text-primary" />
                Trip builder
              </CardTitle>
            </CardHeader>
            <CardContent className="p-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Presets */}
                <div className="space-y-3">
                  <Label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    Quick start
                  </Label>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {presets.map((preset) => (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => setQuery(preset.query)}
                        className="flex flex-col items-center gap-2 rounded-2xl border border-border p-4 text-center transition-all hover:border-primary/40 hover:bg-secondary/50"
                      >
                        <span className="text-2xl">{preset.emoji}</span>
                        <span className="text-sm font-bold">{preset.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="grid gap-6 sm:grid-cols-2">
                  <FormSection icon={Users} label="Group">
                    <FormField label="Group size">
                      <Input
                        type="number"
                        min={1}
                        max={20}
                        value={query.group_size}
                        onChange={(e) =>
                          updateQuery("group_size", parseInt(e.target.value) || 1)
                        }
                        className="rounded-xl h-12"
                      />
                    </FormField>
                    <FormField label="Composition">
                      <Select
                        value={query.group_composition}
                        onValueChange={(value) =>
                          updateQuery("group_composition", value as UserQuery["group_composition"])
                        }
                      >
                        <SelectTrigger className="rounded-xl h-12">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {GROUP_TYPES.map((type) => (
                            <SelectItem key={type.value} value={type.value}>
                              {type.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormField>
                  </FormSection>

                  <FormSection icon={Calendar} label="Timing">
                    <FormField label="Days">
                      <Input
                        type="number"
                        min={2}
                        max={21}
                        value={query.days}
                        onChange={(e) =>
                          updateQuery("days", parseInt(e.target.value) || 2)
                        }
                        className="rounded-xl h-12"
                      />
                    </FormField>
                    <FormField label="Travel month">
                      <Select
                        value={query.travel_month.toString()}
                        onValueChange={(value) =>
                          updateQuery("travel_month", parseInt(value || "1"))
                        }
                      >
                        <SelectTrigger className="rounded-xl h-12">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {MONTHS.map((month, index) => (
                            <SelectItem key={month} value={(index + 1).toString()}>
                              {month}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormField>
                  </FormSection>
                </div>

                <div className="grid gap-6 sm:grid-cols-2">
                  <FormField label="Origin city">
                    <Select
                      value={query.origin_city}
                      onValueChange={(value) => updateQuery("origin_city", value || "")}
                    >
                      <SelectTrigger className="rounded-xl h-12">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ORIGIN_CITIES.map((city) => (
                          <SelectItem key={city} value={city}>
                            {city.charAt(0).toUpperCase() + city.slice(1)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>

                  <FormField label="Travel mode">
                    <Select
                      value={query.travel_mode_pref}
                      onValueChange={(value) =>
                        updateQuery("travel_mode_pref", value as UserQuery["travel_mode_pref"])
                      }
                    >
                      <SelectTrigger className="rounded-xl h-12">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {TRAVEL_MODES.map((mode) => (
                          <SelectItem key={mode.value} value={mode.value}>
                            {mode.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </div>

                <FormSection icon={Wallet} label="Budget & difficulty">
                  <FormField label={`Budget — PKR ${query.budget_pkr.toLocaleString()}`}>
                    <Input
                      type="number"
                      min={20000}
                      max={2000000}
                      step={10000}
                      value={query.budget_pkr}
                      onChange={(e) =>
                        updateQuery("budget_pkr", parseInt(e.target.value) || 0)
                      }
                      className="rounded-xl h-12"
                    />
                  </FormField>
                  <FormField label={`Difficulty tolerance — ${query.difficulty_tolerance}/5`}>
                    <Slider
                      value={[query.difficulty_tolerance]}
                      min={1}
                      max={5}
                      step={1}
                      onValueChange={(value) => updateQuery("difficulty_tolerance", value[0])}
                    />
                  </FormField>
                </FormSection>

                <div className="space-y-3">
                  <Label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    Travel styles
                  </Label>
                  <div className="flex flex-wrap gap-2">
                    {STYLE_TAGS.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleStyle(tag)}
                        className={`rounded-full px-4 py-2 text-xs font-bold capitalize transition-all ${
                          query.style_tags.includes(tag)
                            ? "bg-foreground text-background shadow-md"
                            : "border border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground"
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <ToggleRow
                    label="Foreign traveller"
                    checked={query.is_foreign_traveller}
                    onCheckedChange={(c) => updateQuery("is_foreign_traveller", c)}
                  />
                  <ToggleRow
                    label="Elderly in group"
                    checked={query.elderly_in_group}
                    onCheckedChange={(c) => updateQuery("elderly_in_group", c)}
                  />
                  <ToggleRow
                    label="Full LLM mode"
                    icon={Sparkles}
                    description="Unique AI-generated arguments per agent"
                    checked={fullLlmMode}
                    onCheckedChange={setFullLlmMode}
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full h-14 text-base rounded-xl bg-foreground text-background hover:bg-foreground/90 shadow-xl"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Agents are debating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate my plan
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </Reveal>

        {/* Loading / Empty / Results */}
        <div ref={resultsRef} className="mt-16 scroll-mt-28">
          {!result && !loading && <EmptyState />}
          {loading && <LoadingState />}
          {result && <ResultsDisplay result={result} />}
        </div>
      </div>
    </div>
  );
}

function FormSection({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm font-semibold">{label}</Label>
      {children}
    </div>
  );
}

function ToggleRow({
  label,
  description,
  icon: Icon,
  checked,
  onCheckedChange,
}: {
  label: string;
  description?: string;
  icon?: React.ElementType;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border px-4 py-3">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        <div>
          <p className="text-sm font-semibold leading-none">{label}</p>
          {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
        </div>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}

function EmptyState() {
  return (
    <Reveal>
      <Card className="mx-auto max-w-2xl border-dashed border-border rounded-[2.5rem]">
        <CardContent className="flex flex-col items-center justify-center py-24 text-center">
          <div className="relative mb-6">
            <div className="absolute inset-0 rounded-full bg-primary/15 blur-2xl" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10">
              <MapPin className="h-10 w-10 text-primary" />
            </div>
          </div>
          <h3 className="text-2xl font-bold">Ready when you are</h3>
          <p className="text-muted-foreground max-w-sm mt-2">
            Fill in the trip builder above and the agents will generate your route.
          </p>
        </CardContent>
      </Card>
    </Reveal>
  );
}

function LoadingState() {
  return (
    <Reveal>
      <Card className="mx-auto max-w-2xl border-border rounded-[2.5rem] overflow-hidden">
        <CardContent className="flex flex-col items-center justify-center py-24">
          <div className="relative mb-6">
            <div className="absolute inset-0 rounded-full bg-primary/15 blur-2xl animate-pulse" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10">
              <Brain className="h-10 w-10 text-primary animate-pulse" />
            </div>
          </div>
          <h3 className="text-2xl font-bold">The agents are debating</h3>
          <p className="text-muted-foreground mt-2 text-center max-w-sm">
            Weather, Road, Safety, Budget, and Local Experience agents are scoring your candidates...
          </p>
          <div className="flex gap-2 mt-6 flex-wrap justify-center">
            {["Weather", "Road", "Safety", "Budget", "Local"].map((agent, i) => (
              <div
                key={agent}
                className="flex items-center gap-1.5 rounded-full bg-muted px-3 py-1.5 text-xs font-semibold"
              >
                <Loader2 className="h-3 w-3 animate-spin text-primary" />
                {agent}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </Reveal>
  );
}

function ResultsDisplay({ result }: { result: PlanResponse }) {
  const debate = result.debate_result;
  const candidates = result.candidates || [];
  const winnerId = debate?.debate_trace?.orchestrator?.final_winner_id;
  const allBlocked = debate?.all_blocked;
  const winner = debate?.winner;

  const [selectedCandidateId, setSelectedCandidateId] = useState(
    winnerId || candidates[0]?.candidate_id || ""
  );

  const selectedCandidate =
    candidates.find((c) => c.candidate_id === selectedCandidateId) ||
    winner ||
    candidates[0];

  const selectedStops = getRouteStops(
    selectedCandidate?.route || selectedCandidate?.destinations || []
  );

  if (allBlocked) {
    return (
      <div className="animate-reveal-up space-y-6">
        <Card className="mx-auto max-w-2xl border-rose-200 bg-rose-50/50 rounded-[2.5rem]">
          <CardContent className="flex gap-3 pt-6">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-rose-900">No viable route found</h3>
              <p className="mt-1 text-sm text-rose-800/80">
                {debate?.orchestrator_reasoning ||
                  "All candidates were blocked. Try adjusting your budget or constraints."}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <Reveal>
        <div className="text-center mb-2">
          <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">
            Your plan
          </p>
          <h2 className="text-3xl font-extrabold sm:text-4xl">
            Here&apos;s what the agents decided
          </h2>
        </div>
      </Reveal>

      {selectedCandidate && selectedStops.length > 0 && (
        <Reveal delay={100}>
          <RouteHero
            candidate={selectedCandidate}
            isWinner={selectedCandidate.candidate_id === winnerId}
            mapStops={selectedStops}
          />
        </Reveal>
      )}

      {candidates.length > 0 && (
        <Reveal delay={150}>
          <CandidateSelector
            candidates={candidates}
            selectedId={selectedCandidateId}
            winnerId={winnerId}
            onSelect={setSelectedCandidateId}
          />
        </Reveal>
      )}

      <Reveal delay={200}>
        {winner && <ItineraryPreview candidate={winner} />}
      </Reveal>

      <Reveal delay={250}>
        {debate && <AgentScorecard debate={debate} />}
      </Reveal>

      <Reveal delay={300}>
        {debate && <WhyNotList debate={debate} />}
      </Reveal>

      <Reveal delay={350}>
        {debate && <DissentBox debate={debate} />}
      </Reveal>

      <Reveal delay={400}>
        {debate && <OrchestratorReasoning reasoning={debate.orchestrator_reasoning} />}
      </Reveal>

      <Reveal delay={450}>
        <DeveloperDetails
          result={{
            recommendation_trace: result.recommendation_trace,
            debate_trace: debate?.debate_trace,
          }}
        />
      </Reveal>
    </div>
  );
}
