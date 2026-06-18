"use client";

import { useState } from "react";
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
  Trophy,
  Brain,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
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
  CandidateCard,
  AgentScorecard,
  DissentBox,
  WhyNotList,
} from "@/components/plan-results";

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

const presets: { label: string; description: string; query: UserQuery }[] = [
  {
    label: "Family Scenic",
    description: "Relaxed, scenic, elderly-friendly",
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
    description: "Trekking, adventurous, budget",
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
    description: "Food, photography, social",
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

export default function PlanPage() {
  const [query, setQuery] = useState<UserQuery>(defaultQuery);
  const [fullLlmMode, setFullLlmMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanResponse | null>(null);

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
    <div className="container py-10 lg:py-14">
      <div className="mb-10 max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Plan your trip
        </h1>
        <p className="text-muted-foreground mt-3 text-lg">
          Tell the agents about your group and preferences. They&apos;ll
          debate three diverse routes and pick the best one — transparently.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[420px_1fr]">
        {/* Form */}
        <div className="lg:sticky lg:top-24 lg:self-start">
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings2 className="h-5 w-5 text-primary" />
                Trip details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Presets */}
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                    Quick presets
                  </Label>
                  <div className="grid gap-2">
                    {presets.map((preset) => (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => setQuery(preset.query)}
                        className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2.5 text-left text-sm transition-all hover:border-primary/40 hover:bg-primary/[0.03]"
                      >
                        <span className="font-medium">{preset.label}</span>
                        <span className="text-xs text-muted-foreground">
                          {preset.description}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                <Separator />

                {/* Group section */}
                <FormSection icon={Users} label="Group">
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Group size">
                      <Input
                        type="number"
                        min={1}
                        max={20}
                        value={query.group_size}
                        onChange={(e) =>
                          updateQuery(
                            "group_size",
                            parseInt(e.target.value) || 1
                          )
                        }
                      />
                    </FormField>
                    <FormField label="Composition">
                      <Select
                        value={query.group_composition}
                        onValueChange={(value) =>
                          updateQuery(
                            "group_composition",
                            value as UserQuery["group_composition"]
                          )
                        }
                      >
                        <SelectTrigger>
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
                  </div>
                </FormSection>

                {/* Trip section */}
                <FormSection icon={Calendar} label="Timing">
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="Days">
                      <Input
                        type="number"
                        min={2}
                        max={21}
                        value={query.days}
                        onChange={(e) =>
                          updateQuery("days", parseInt(e.target.value) || 2)
                        }
                      />
                    </FormField>
                    <FormField label="Travel month">
                      <Select
                        value={query.travel_month.toString()}
                        onValueChange={(value) =>
                          updateQuery("travel_month", parseInt(value || "1"))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {MONTHS.map((month, index) => (
                            <SelectItem
                              key={month}
                              value={(index + 1).toString()}
                            >
                              {month}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormField>
                  </div>
                  <FormField label="Origin city">
                    <Select
                      value={query.origin_city}
                      onValueChange={(value) =>
                        updateQuery("origin_city", value || "")
                      }
                    >
                      <SelectTrigger>
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
                        updateQuery(
                          "travel_mode_pref",
                          value as UserQuery["travel_mode_pref"]
                        )
                      }
                    >
                      <SelectTrigger>
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
                </FormSection>

                {/* Budget section */}
                <FormSection icon={Wallet} label="Budget & difficulty">
                  <FormField
                    label={`Budget — PKR ${query.budget_pkr.toLocaleString()}`}
                  >
                    <Input
                      type="number"
                      min={20000}
                      max={2000000}
                      step={10000}
                      value={query.budget_pkr}
                      onChange={(e) =>
                        updateQuery(
                          "budget_pkr",
                          parseInt(e.target.value) || 0
                        )
                      }
                    />
                  </FormField>
                  <FormField
                    label={`Difficulty tolerance — ${query.difficulty_tolerance}/5`}
                  >
                    <Slider
                      value={[query.difficulty_tolerance]}
                      min={1}
                      max={5}
                      step={1}
                      onValueChange={(value) =>
                        updateQuery("difficulty_tolerance", value[0])
                      }
                    />
                  </FormField>
                </FormSection>

                {/* Styles */}
                <div className="space-y-3">
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                    Travel styles
                  </Label>
                  <div className="flex flex-wrap gap-2">
                    {STYLE_TAGS.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleStyle(tag)}
                        className={`rounded-full px-3 py-1.5 text-xs font-medium capitalize transition-all ${
                          query.style_tags.includes(tag)
                            ? "bg-primary text-primary-foreground shadow-sm"
                            : "border border-border/60 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>

                <Separator />

                {/* Toggles */}
                <div className="space-y-3">
                  <ToggleRow
                    label="Foreign traveller"
                    checked={query.is_foreign_traveller}
                    onCheckedChange={(c) =>
                      updateQuery("is_foreign_traveller", c)
                    }
                  />
                  <ToggleRow
                    label="Elderly in group"
                    checked={query.elderly_in_group}
                    onCheckedChange={(c) =>
                      updateQuery("elderly_in_group", c)
                    }
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
                  className="w-full h-11 text-base"
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
                      Plan my trip
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="space-y-6">
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
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
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
      <Label className="text-sm">{label}</Label>
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
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2.5">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        <div>
          <p className="text-sm font-medium leading-none">{label}</p>
          {description && (
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          )}
        </div>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}

function EmptyState() {
  return (
    <Card className="border-dashed border-border/60">
      <CardContent className="flex flex-col items-center justify-center py-24 text-center">
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-full bg-primary/20 blur-2xl" />
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <MapPin className="h-8 w-8 text-primary" />
          </div>
        </div>
        <h3 className="text-xl font-semibold">Ready to plan</h3>
        <p className="text-muted-foreground max-w-sm mt-2">
          Fill in your trip details and the agents will generate three diverse
          route options with a full transparency scorecard.
        </p>
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <Card className="border-border/60">
      <CardContent className="flex flex-col items-center justify-center py-24">
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-full bg-primary/20 blur-2xl animate-pulse" />
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <Brain className="h-8 w-8 text-primary animate-pulse" />
          </div>
        </div>
        <h3 className="text-xl font-semibold">The agents are debating</h3>
        <p className="text-muted-foreground mt-2 text-center max-w-sm">
          Weather, Road, Safety, Budget, and Local Experience agents are
          scoring your candidate routes...
        </p>
        <div className="flex gap-2 mt-6">
          {["Weather", "Road", "Safety", "Budget", "Local"].map((agent, i) => (
            <div
              key={agent}
              className="flex items-center gap-1.5 rounded-full bg-muted px-3 py-1.5 text-xs font-medium"
              style={{ animationDelay: `${i * 200}ms` }}
            >
              <Loader2 className="h-3 w-3 animate-spin text-primary" />
              {agent}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ResultsDisplay({ result }: { result: PlanResponse }) {
  const debate = result.debate_result;
  const candidates = result.candidates || [];
  const winnerId = debate?.debate_trace?.orchestrator?.final_winner_id;
  const allBlocked = debate?.all_blocked;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Winner / Status banner */}
      {allBlocked ? (
        <Card className="border-rose-200 bg-rose-50/50">
          <CardContent className="flex gap-3 pt-6">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-rose-900">
                No viable route found
              </h3>
              <p className="mt-1 text-sm text-rose-800/80">
                {debate?.orchestrator_reasoning ||
                  "All candidates were blocked. Try adjusting your budget or constraints."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        debate?.winner && (
          <Card className="border-primary/30 bg-primary/[0.02]">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Trophy className="h-4 w-4" />
                </div>
                <div>
                  <CardTitle className="text-lg">Recommended route</CardTitle>
                  <CardDescription>
                    The orchestrator selected this route after the debate.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <CandidateCard
                candidate={debate.winner}
                isWinner
              />
            </CardContent>
          </Card>
        )
      )}

      {/* All candidates */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          All candidates ({candidates.length})
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {candidates.map((cand) => (
            <CandidateCard
              key={cand.candidate_id}
              candidate={cand}
              isWinner={cand.candidate_id === winnerId}
            />
          ))}
        </div>
      </div>

      {/* Scorecard */}
      {debate && <AgentScorecard debate={debate} />}

      {/* Dissent */}
      {debate && <DissentBox debate={debate} />}

      {/* Why not */}
      {debate && <WhyNotList debate={debate} />}

      {/* Orchestrator reasoning */}
      {debate?.orchestrator_reasoning && (
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              Orchestrator reasoning
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {debate.orchestrator_reasoning}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Transparency trace */}
      {result.recommendation_trace && (
        <CollapsibleSection title="How candidates were selected">
          <pre className="text-xs overflow-auto bg-muted rounded-lg p-4 max-h-[400px]">
            {JSON.stringify(result.recommendation_trace, null, 2)}
          </pre>
        </CollapsibleSection>
      )}

      {/* Raw JSON */}
      <CollapsibleSection title="Raw response (debug)">
        <pre className="text-xs overflow-auto bg-muted rounded-lg p-4 max-h-[500px]">
          {JSON.stringify(result, null, 2)}
        </pre>
      </CollapsibleSection>
    </div>
  );
}

function CollapsibleSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <details className="group border border-border/60 rounded-lg px-4 py-3">
      <summary className="cursor-pointer text-base font-semibold list-none flex items-center justify-between hover:no-underline">
        {title}
        <span className="text-muted-foreground text-sm transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}
