"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, MapPin, Users, Compass, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SummaryBar } from "@/components/canvas/SummaryBar";
import { PlanningCard } from "@/components/canvas/PlanningCard";
import { TripBasics } from "@/components/canvas/cards/TripBasics";
import { GroupContext } from "@/components/canvas/cards/GroupContext";
import { ExperiencePreferences } from "@/components/canvas/cards/ExperiencePreferences";
import { LivePreview } from "@/components/canvas/LivePreview";
import { DEFAULT_QUERY } from "@/lib/types";
import type { UserQuery } from "@/lib/types";
import { setPendingPlan } from "@/lib/storage";

export default function PlanPage() {
  const router = useRouter();
  const [query, setQuery] = useState<UserQuery>(DEFAULT_QUERY);
  const [generating, setGenerating] = useState(false);

  const updateQuery = useCallback(
    <K extends keyof UserQuery>(key: K, value: UserQuery[K]) => {
      setQuery((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const toggleStyle = useCallback((tag: string) => {
    setQuery((prev) => ({
      ...prev,
      style_tags: prev.style_tags.includes(tag)
        ? prev.style_tags.filter((t) => t !== tag)
        : [...prev.style_tags, tag],
    }));
  }, []);

  const handleGenerate = () => {
    setGenerating(true);
    setPendingPlan(query);
    router.push("/processing");
  };

  const card1Complete = query.origin_city !== "" && query.budget_pkr > 0 && query.days >= 2;
  const card2Complete = query.group_size >= 1;
  const card3Complete = query.style_tags.length > 0 && query.difficulty_tolerance >= 1;

  const card1Summary = `${capitalize(query.origin_city)} · PKR ${(query.budget_pkr / 1000).toFixed(0)}k · ${query.days} days`;
  const card2Summary = `${capitalize(query.group_composition)} · ${query.group_size} ${query.group_size === 1 ? "person" : "people"}`;
  const card3Summary = `${query.style_tags.length} styles · ${["Chill", "Relaxed", "Balanced", "Packed", "Extreme"][query.difficulty_tolerance - 1]} · ${capitalize(query.travel_mode_pref)}`;

  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="container">
        {/* Summary bar */}
        <SummaryBar query={query} updateQuery={updateQuery} />

        {/* Header */}
        <div className="text-center mt-8 mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4">
            <Compass className="h-3.5 w-3.5 text-primary" />
            Smart Planning Canvas
          </div>
          <h1 className="text-4xl font-display font-bold tracking-tight sm:text-5xl">
            Shape your trip in real-time
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-lg text-muted-foreground">
            Edit anything instantly. The preview updates as you go.
          </p>
        </div>

        {/* Main layout: cards + live preview */}
        <div className="grid lg:grid-cols-[1fr_380px] gap-6 items-start">
          {/* Left: planning cards */}
          <div className="space-y-5">
            <PlanningCard
              title="Trip Basics"
              subtitle="Origin, month, budget, and days"
              icon={<MapPin className="h-5 w-5" />}
              summary={card1Summary}
              complete={card1Complete}
              defaultOpen={true}
            >
              <TripBasics query={query} updateQuery={updateQuery} />
            </PlanningCard>

            <PlanningCard
              title="Group Context"
              subtitle="Who's traveling and what they need"
              icon={<Users className="h-5 w-5" />}
              summary={card2Summary}
              complete={card2Complete}
              defaultOpen={false}
            >
              <GroupContext query={query} updateQuery={updateQuery} />
            </PlanningCard>

            <PlanningCard
              title="Experience Preferences"
              subtitle="Style, intensity, and travel mode"
              icon={<Sparkles className="h-5 w-5" />}
              summary={card3Summary}
              complete={card3Complete}
              defaultOpen={false}
            >
              <ExperiencePreferences
                query={query}
                updateQuery={updateQuery}
                toggleStyle={toggleStyle}
              />
            </PlanningCard>

            {/* Generate CTA */}
            <div className="pt-4">
              <Button
                onClick={handleGenerate}
                disabled={generating}
                className="w-full h-16 text-base rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-xl shadow-primary/20 border-glow text-lg font-bold transition-all hover:scale-[1.01]"
              >
                {generating ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-5 w-5" />
                    Generate Final Plan
                    <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </Button>
              <p className="text-center text-xs text-muted-foreground mt-3">
                Five AI agents will analyze and debate your best route
              </p>
            </div>
          </div>

          {/* Right: live preview (desktop) */}
          <div className="hidden lg:block">
            <LivePreview query={query} />
          </div>

          {/* Below: live preview (mobile) */}
          <div className="lg:hidden">
            <LivePreview query={query} />
          </div>
        </div>
      </div>
    </div>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
