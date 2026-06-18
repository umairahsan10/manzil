"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Star, Loader2, MessageSquare, TrendingUp, ThumbsUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { submitFeedback, getFeedbackStats } from "@/lib/api";
import { FeedbackStatsResponse, PlanResponse } from "@/lib/types";

const VALID_FEEDBACK_TAGS = [
  { value: "would-recommend", label: "Would recommend" },
  { value: "great-views", label: "Great views" },
  { value: "loved-the-food", label: "Loved the food" },
  { value: "family-friendly", label: "Family friendly" },
  { value: "too-rushed", label: "Too rushed" },
  { value: "too-slow", label: "Too slow" },
  { value: "weather-was-wrong", label: "Weather was wrong" },
  { value: "budget-overran", label: "Budget overran" },
  { value: "road-was-rough", label: "Road was rough" },
  { value: "not-again", label: "Not again" },
];

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
      .catch(() => {
        // ignore
      });
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
    <div className="container py-10 lg:py-14 max-w-2xl">
      <div className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Post-trip feedback
        </h1>
        <p className="text-muted-foreground mt-3 text-lg">
          Help the agents learn from your experience. Your feedback trains
          the case base for future recommendations.
        </p>
      </div>

      {!lastTrip && (
        <Card className="border-dashed border-border/60">
          <CardContent className="flex flex-col items-center justify-center py-20 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted mb-4">
              <MessageSquare className="h-7 w-7 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No recent trip</h3>
            <p className="text-muted-foreground max-w-sm mt-2 mb-6">
              Plan a trip first so you can rate and tag the result.
            </p>
            <Button asChild>
              <Link href="/plan">Plan a trip</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {lastTrip && !submitted && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>How was your trip?</CardTitle>
            <CardDescription>
              Rate the plan and select tags that best describe your experience.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Rating */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Rating</Label>
                  <div className="flex items-center gap-1.5">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`h-5 w-5 transition-colors ${
                          star <= Math.round(rating)
                            ? "fill-amber-400 text-amber-400"
                            : "text-muted-foreground/30"
                        }`}
                      />
                    ))}
                    <span className="ml-2 text-sm font-medium">
                      {rating.toFixed(1)}
                    </span>
                  </div>
                </div>
                <Slider
                  value={[rating]}
                  min={1}
                  max={5}
                  step={0.5}
                  onValueChange={(value) => setRating(value[0])}
                />
              </div>

              <Separator />

              {/* Tags */}
              <div className="space-y-3">
                <Label>What best describes the plan?</Label>
                <div className="flex flex-wrap gap-2">
                  {VALID_FEEDBACK_TAGS.map((tag) => (
                    <button
                      key={tag.value}
                      type="button"
                      onClick={() => toggleTag(tag.value)}
                      className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
                        tags.includes(tag.value)
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "border border-border/60 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                      }`}
                    >
                      {tag.label}
                    </button>
                  ))}
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-11 text-base"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <ThumbsUp className="mr-2 h-4 w-4" />
                    Submit feedback
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {submitted && (
        <Card className="border-emerald-200 bg-emerald-50/50">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 mb-4">
              <Star className="h-7 w-7 text-emerald-600 fill-emerald-600" />
            </div>
            <h3 className="text-lg font-semibold text-emerald-900">
              Thanks for your feedback!
            </h3>
            <p className="text-emerald-800/70 max-w-sm mt-2 mb-6">
              Your feedback has been recorded and will help future
              recommendations.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" asChild>
                <Link href="/plan">Plan another trip</Link>
              </Button>
              <Button onClick={() => setSubmitted(false)}>
                Submit another
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {stats && (
        <>
          <div className="my-8 flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
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
            <Card className="mt-4 border-border/60">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Top tags</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {stats.top_tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground"
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
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="text-sm font-medium leading-none">{children}</label>
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
    <Card className="border-border/60">
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-2xl font-bold leading-none">{value}</p>
            <p className="text-sm text-muted-foreground mt-1">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
