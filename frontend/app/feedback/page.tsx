"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Star,
  Loader2,
  MessageSquare,
  TrendingUp,
  ThumbsUp,
  ArrowRight,
  Send,
  RotateCcw,
  Heart,
  Compass,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { submitFeedback, getFeedbackStats } from "@/lib/api";
import { FeedbackStatsResponse, PlanResponse } from "@/lib/types";
import { PexelsImage } from "@/components/pexels-image";

const VALID_FEEDBACK_TAGS = [
  { value: "would-recommend", label: "Would recommend", emoji: "👍" },
  { value: "great-views", label: "Great views", emoji: "🏔️" },
  { value: "loved-the-food", label: "Loved the food", emoji: "🍲" },
  { value: "family-friendly", label: "Family friendly", emoji: "👨‍👩‍👧‍👦" },
  { value: "too-rushed", label: "Too rushed", emoji: "⏱️" },
  { value: "too-slow", label: "Too slow", emoji: "🐢" },
  { value: "weather-was-wrong", label: "Weather was wrong", emoji: "🌧️" },
  { value: "budget-overran", label: "Budget overran", emoji: "💸" },
  { value: "road-was-rough", label: "Road was rough", emoji: "🛣️" },
  { value: "not-again", label: "Not again", emoji: "👎" },
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

export default function FeedbackPage() {
  const [lastTrip, setLastTrip] = useState<PlanResponse | null>(null);
  const [rating, setRating] = useState(4);
  const [tags, setTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [stats, setStats] = useState<FeedbackStatsResponse | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("manzil:last-trip");
    if (raw) {
      try {
        setLastTrip(JSON.parse(raw));
      } catch {
        // ignore
      }
    }
    getFeedbackStats()
      .then(setStats)
      .catch(() => {});
  }, []);

  const toggleTag = (tag: string) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lastTrip) {
      toast.error("No recent trip found. Plan a trip first.");
      return;
    }

    setLoading(true);
    try {
      await submitFeedback({
        trip_id: lastTrip.trip_id,
        rating,
        tags,
      });
      setSubmitted(true);
      const updatedStats = await getFeedbackStats();
      setStats(updatedStats);
      toast.success("Thank you for your feedback!");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to submit feedback"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pt-24 pb-20">
      {/* Banner */}
      <section className="relative h-64 lg:h-80 overflow-hidden">
        <PexelsImage
          query="Pakistan northern areas mountain traveler landscape"
          alt="Traveler in northern Pakistan"
          containerClassName="absolute inset-0"
          className="scale-105"
          overlay={
            <>
              <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent" />
              <div className="absolute inset-0 bg-gradient-to-r from-background/70 via-transparent to-background/50" />
              <div className="absolute inset-0 bg-noise" />
            </>
          }
        />
        <div className="container relative z-10 flex h-full flex-col justify-end pb-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4 w-fit">
            <Compass className="h-3.5 w-3.5 text-primary" />
            Share your experience
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
            How was your trip?
          </h1>
          <p className="mt-3 max-w-xl text-lg text-muted-foreground">
            Help the agents learn from your experience.
          </p>
        </div>
      </section>

      <section className="container py-12 lg:py-16">
        <div className="mx-auto max-w-2xl">
          {!lastTrip && (
            <Reveal>
              <Card className="border-dashed border-border rounded-[2.5rem]">
                <CardContent className="flex flex-col items-center justify-center py-24 text-center">
                  <div className="relative mb-6">
                    <div className="absolute inset-0 rounded-full bg-primary/15 blur-2xl" />
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10">
                      <MessageSquare className="h-10 w-10 text-primary" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold">No recent trip</h3>
                  <p className="text-muted-foreground max-w-sm mt-2 mb-6">
                    Plan a trip first so you can rate and tag the result.
                  </p>
                  <Button className="rounded-full group" asChild>
                    <Link href="/plan">
                      Plan a trip
                      <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </Reveal>
          )}

          {lastTrip && !submitted && (
            <Reveal>
              <Card className="border-border shadow-xl shadow-primary/5 overflow-hidden rounded-[2.5rem]">
                <CardHeader className="border-b border-border bg-secondary/30 px-8 py-6">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <ThumbsUp className="h-5 w-5 text-primary" />
                    Rate your plan
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-8">
                  <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Label>Rating</Label>
                        <span className="text-2xl font-black text-primary">{rating.toFixed(1)}</span>
                      </div>
                      <div className="flex items-center justify-center gap-2">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            onClick={() => setRating(star)}
                            className="p-1 transition-transform hover:scale-110"
                          >
                            <Star
                              className={`h-10 w-10 transition-colors ${
                                star <= Math.round(rating)
                                  ? "fill-amber-400 text-amber-400"
                                  : "text-muted-foreground/30"
                              }`}
                            />
                          </button>
                        ))}
                      </div>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                      <Label>What best describes the plan?</Label>
                      <div className="flex flex-wrap gap-2">
                        {VALID_FEEDBACK_TAGS.map((tag) => (
                          <button
                            key={tag.value}
                            type="button"
                            onClick={() => toggleTag(tag.value)}
                            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all ${
                              tags.includes(tag.value)
                                ? "bg-foreground text-background shadow-md"
                                : "border border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground"
                            }`}
                          >
                            <span>{tag.emoji}</span>
                            {tag.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <Button
                      type="submit"
                      className="w-full h-14 text-base rounded-xl bg-foreground text-background hover:bg-foreground/90 shadow-xl"
                      disabled={loading}
                    >
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        <>
                          <Send className="mr-2 h-4 w-4" />
                          Submit feedback
                        </>
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </Reveal>
          )}

          {submitted && (
            <Reveal>
              <Card className="border-emerald-200 bg-emerald-50/50 rounded-[2.5rem]">
                <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="relative mb-6">
                    <div className="absolute inset-0 rounded-full bg-emerald-400/30 blur-2xl" />
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-emerald-100">
                      <Heart className="h-10 w-10 text-emerald-600 fill-emerald-600" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold text-emerald-900">
                    Thanks for your feedback!
                  </h3>
                  <p className="text-emerald-800/70 max-w-sm mt-2 mb-6">
                    Your feedback has been recorded and will help future recommendations.
                  </p>
                  <div className="flex gap-3">
                    <Button variant="outline" asChild className="rounded-full">
                      <Link href="/plan">Plan another trip</Link>
                    </Button>
                    <Button
                      onClick={() => {
                        setSubmitted(false);
                        setTags([]);
                        setRating(4);
                      }}
                      className="rounded-full"
                    >
                      <RotateCcw className="mr-2 h-4 w-4" />
                      Submit another
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </Reveal>
          )}

          {stats && stats.count > 0 && (
            <>
              <div className="my-8 flex items-center gap-3">
                <Separator className="flex-1" />
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  Community
                </span>
                <Separator className="flex-1" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <StatCard
                  icon={TrendingUp}
                  label="Total ratings"
                  value={stats.count.toString()}
                />
                <StatCard
                  icon={Star}
                  label="Average rating"
                  value={stats.avg_rating.toFixed(1)}
                />
              </div>
              {stats.top_tags.length > 0 && (
                <Card className="mt-4 border-border rounded-[2.5rem]">
                  <CardHeader className="pb-3 px-6 pt-6">
                    <CardTitle className="text-sm">Top tags</CardTitle>
                  </CardHeader>
                  <CardContent className="px-6 pb-6">
                    <div className="flex flex-wrap gap-2">
                      {stats.top_tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold text-secondary-foreground"
                        >
                          {tag.replace(/-/g, " ")}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="text-sm font-bold leading-none">{children}</label>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <Card className="border-border rounded-[2.5rem]">
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
            <Icon className="h-6 w-6 text-primary" />
          </div>
          <div>
            <p className="text-3xl font-extrabold leading-none">{value}</p>
            <p className="text-sm text-muted-foreground mt-1">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
