"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Star, Loader2, Send, RotateCcw, Heart, TrendingUp, MessageSquare, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { submitFeedback, getFeedbackStats } from "@/lib/api";
import { getLastTrip } from "@/lib/storage";
import type { FeedbackStatsResponse, PlanResponse } from "@/lib/types";

const routeIssues = [
  { value: "road-was-rough", label: "Road blocked", emoji: "🛣️" },
  { value: "weather-was-wrong", label: "Weather changed", emoji: "🌧️" },
  { value: "budget-overran", label: "Overspent", emoji: "💸" },
  { value: "stay-mismatch", label: "Stay mismatch", emoji: "🏨" },
  { value: "too-rushed", label: "Itinerary too rushed", emoji: "⏱️" },
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

function Reveal({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useReveal();
  return (
    <div ref={ref} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

export default function FeedbackPage() {
  const [lastTrip, setLastTrip] = useState<PlanResponse | null>(null);
  const [rating, setRating] = useState(4);
  const [budgetAccuracy, setBudgetAccuracy] = useState(4);
  const [safetyAccuracy, setSafetyAccuracy] = useState(4);
  const [experienceQuality, setExperienceQuality] = useState(4);
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [stats, setStats] = useState<FeedbackStatsResponse | null>(null);

  useEffect(() => {
    const trip = getLastTrip();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (trip) setLastTrip(trip);
    getFeedbackStats().then(setStats).catch(() => {});
  }, []);

  const toggleTag = (tag: string) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lastTrip) return;

    setLoading(true);
    try {
      await submitFeedback({
        trip_id: lastTrip.trip_id,
        rating,
        budget_accuracy: budgetAccuracy,
        safety_accuracy: safetyAccuracy,
        experience_quality: experienceQuality,
        tags,
        comment: comment || undefined,
      });
      setSubmitted(true);
      const updatedStats = await getFeedbackStats();
      setStats(updatedStats);
    } catch {
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="container">
        {/* Header */}
        <div className="text-center mt-8 mb-10">
          <div className="inline-flex items-center gap-2 rounded-full glass px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4">
            <MessageSquare className="h-3.5 w-3.5 text-primary" />
            Post-Trip Feedback
          </div>
          <h1 className="text-4xl font-display font-bold tracking-tight sm:text-5xl">
            How was your trip?
          </h1>
          <p className="mt-3 max-w-xl mx-auto text-lg text-muted-foreground">
            Help the agents learn from your experience.
          </p>
        </div>

        <div className="mx-auto max-w-2xl space-y-6">
          {/* No trip state */}
          {!lastTrip && !submitted && (
            <Reveal>
              <div className="glass-card rounded-3xl p-8 text-center">
                <div className="flex h-16 w-16 mx-auto items-center justify-center rounded-2xl bg-secondary mb-4">
                  <MessageSquare className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="font-display text-xl font-bold mb-2">No recent trip</h3>
                <p className="text-muted-foreground mb-6">Plan a trip first so you can rate and tag the result.</p>
                <Button className="rounded-full group" asChild>
                  <Link href="/plan">
                    Plan a trip
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </Link>
                </Button>
              </div>
            </Reveal>
          )}

          {/* Feedback form */}
          {lastTrip && !submitted && (
            <Reveal>
              <form onSubmit={handleSubmit} className="glass-card rounded-3xl p-6 sm:p-8 space-y-8">
                {/* Star rating */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <label className="text-sm font-bold">Overall Rating</label>
                    <span className="text-2xl font-display font-bold text-primary">{rating.toFixed(1)}</span>
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
                          className={cn(
                            "h-10 w-10 transition-colors",
                            star <= Math.round(rating)
                              ? "fill-warning text-warning"
                              : "text-muted-foreground/30"
                          )}
                        />
                      </button>
                    ))}
                  </div>
                </div>

                <div className="h-px bg-border/60" />

                {/* Accuracy sliders */}
                <div>
                  <label className="text-sm font-bold mb-4 block">Accuracy Ratings</label>
                  <div className="space-y-6">
                    <AccuracySlider
                      label="Budget accuracy"
                      value={budgetAccuracy}
                      onChange={setBudgetAccuracy}
                    />
                    <AccuracySlider
                      label="Safety accuracy"
                      value={safetyAccuracy}
                      onChange={setSafetyAccuracy}
                    />
                    <AccuracySlider
                      label="Experience quality"
                      value={experienceQuality}
                      onChange={setExperienceQuality}
                    />
                  </div>
                </div>

                <div className="h-px bg-border/60" />

                {/* Route issues checklist */}
                <div>
                  <label className="text-sm font-bold mb-4 block">Route Issues</label>
                  <div className="flex flex-wrap gap-2">
                    {routeIssues.map((issue) => (
                      <button
                        key={issue.value}
                        type="button"
                        onClick={() => toggleTag(issue.value)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all",
                          tags.includes(issue.value)
                            ? "bg-primary text-primary-foreground shadow-md"
                            : "bg-secondary text-foreground hover:bg-secondary/70"
                        )}
                      >
                        <span>{issue.emoji}</span>
                        {issue.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Open text */}
                <div>
                  <label className="text-sm font-bold mb-3 block">Notes</label>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    rows={4}
                    placeholder="What worked well? What could be better?"
                    className="w-full rounded-2xl bg-secondary/50 border border-border p-4 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                  />
                </div>

                {/* Submit */}
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full h-14 text-base rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-xl shadow-primary/20"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Submit Feedback
                    </>
                  )}
                </Button>
              </form>
            </Reveal>
          )}

          {/* Confirmation */}
          {submitted && (
            <Reveal>
              <div className="glass-card rounded-3xl p-8 text-center">
                <div className="relative mb-6">
                  <div className="absolute inset-0 rounded-full bg-primary/20 blur-2xl" />
                  <div className="relative flex h-20 w-20 mx-auto items-center justify-center rounded-3xl bg-primary/10">
                    <Heart className="h-10 w-10 text-primary fill-primary" />
                  </div>
                </div>
                <h3 className="font-display text-2xl font-bold mb-2">Thank you!</h3>
                <p className="text-muted-foreground max-w-sm mx-auto mb-6">
                  Your feedback improves future recommendations for every traveler.
                </p>
                <div className="flex gap-3 justify-center">
                  <Button variant="outline" asChild className="rounded-full">
                    <Link href="/plan">Plan another trip</Link>
                  </Button>
                  <Button
                    onClick={() => {
                      setSubmitted(false);
                      setTags([]);
                      setRating(4);
                      setBudgetAccuracy(4);
                      setSafetyAccuracy(4);
                      setExperienceQuality(4);
                      setComment("");
                    }}
                    className="rounded-full"
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Submit another
                  </Button>
                </div>
              </div>
            </Reveal>
          )}

          {/* Community stats */}
          {stats && stats.count > 0 && (
            <>
              <div className="flex items-center gap-3 my-6">
                <div className="flex-1 h-px bg-border/60" />
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Community</span>
                <div className="flex-1 h-px bg-border/60" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-card rounded-2xl p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                      <TrendingUp className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="text-2xl font-display font-bold">{stats.count}</p>
                      <p className="text-xs text-muted-foreground">Total ratings</p>
                    </div>
                  </div>
                </div>
                <div className="glass-card rounded-2xl p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-warning/10">
                      <Star className="h-6 w-6 text-warning fill-warning" />
                    </div>
                    <div>
                      <p className="text-2xl font-display font-bold">{stats.avg_rating.toFixed(1)}</p>
                      <p className="text-xs text-muted-foreground">Average rating</p>
                    </div>
                  </div>
                </div>
              </div>
              {stats.top_tags.length > 0 && (
                <div className="glass-card rounded-2xl p-5">
                  <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">Top tags</p>
                  <div className="flex flex-wrap gap-2">
                    {stats.top_tags.map((tag) => (
                      <span key={tag} className="rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold">
                        {tag.replace(/-/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function AccuracySlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-muted-foreground">{label}</span>
        <span className="text-lg font-display font-bold text-foreground">{value.toFixed(1)}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-muted-foreground">1</span>
        <input
          type="range"
          min={1}
          max={5}
          step={0.5}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 h-2 rounded-full appearance-none cursor-pointer accent-primary"
          style={{
            background: `linear-gradient(to right, #15803D 0%, #15803D ${((value - 1) / 4) * 100}%, #F3F1EC ${((value - 1) / 4) * 100}%, #F3F1EC 100%)`,
          }}
        />
        <span className="text-xs font-bold text-muted-foreground">5</span>
      </div>
    </div>
  );
}
