import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Brain,
  MapPin,
  ShieldAlert,
  Sparkles,
  Users,
  Wind,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "Multi-Agent Debate",
    description:
      "Five specialist agents argue the merits of each route before an orchestrator picks the winner.",
  },
  {
    icon: ShieldAlert,
    title: "Risk-Aware Planning",
    description:
      "Weather, road conditions, safety, budget, and local experience are evaluated independently.",
  },
  {
    icon: MapPin,
    title: "Transparent Routes",
    description:
      "See exactly why each candidate was selected and why the runner-ups lost.",
  },
  {
    icon: Wind,
    title: "Replan on Disruption",
    description:
      "Road closed? Budget cut? Simulate disruptions and get a revised plan in seconds.",
  },
  {
    icon: Users,
    title: "Built for Your Group",
    description:
      "Families, solo travelers, friends — the plan adapts to group size, budget, and travel style.",
  },
  {
    icon: Sparkles,
    title: "Live AI Reasoning",
    description:
      "Watch the agents reason in real time when Full LLM mode is enabled.",
  },
];

const steps = [
  {
    number: "01",
    title: "Tell us about your trip",
    description:
      "Share your group size, budget, days, and travel style. No signup required.",
  },
  {
    number: "02",
    title: "Agents debate your options",
    description:
      "Weather, road, safety, budget, and local experts each score three diverse routes.",
  },
  {
    number: "03",
    title: "Get a transparent plan",
    description:
      "Receive a day-by-day itinerary with a full scorecard explaining every decision.",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border/60">
        <div className="absolute inset-0 bg-grid mask-fade-bottom opacity-[0.4]" />
        <div className="absolute inset-0 bg-radial-fade" />
        <div className="container relative py-24 lg:py-32">
          <div className="mx-auto max-w-3xl text-center">
            <div className="inline-flex items-center rounded-full border border-border/80 bg-background/60 px-3.5 py-1.5 text-sm font-medium text-muted-foreground mb-8 backdrop-blur animate-fade-in">
              <Sparkles className="mr-2 h-3.5 w-3.5 text-accent" />
              AI-powered travel planning for northern Pakistan
            </div>
            <h1 className="text-balance text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl animate-fade-in-up">
              Plan your next northern Pakistan adventure with{" "}
              <span className="bg-gradient-to-r from-primary via-primary to-accent bg-clip-text text-transparent">
                agents
              </span>
              .
            </h1>
            <p className="text-pretty mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl animate-fade-in-up [animation-delay:100ms]">
              Manzil combines route intelligence, weather, road knowledge,
              safety data, and local experience into a single transparent trip
              plan — then explains every decision.
            </p>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row justify-center animate-fade-in-up [animation-delay:200ms]">
              <Button size="lg" asChild className="group">
                <Link href="/plan">
                  Start Planning
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/feedback">Share Feedback</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Trust bar */}
      <section className="border-b border-border/60 bg-muted/30">
        <div className="container py-6">
          <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-muted-foreground">
            {[
              "5 Specialist Agents",
              "Real Weather Data",
              "Safety-First Design",
              "Transparent Reasoning",
              "No Signup Required",
            ].map((item) => (
              <div key={item} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                <span className="font-medium">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 lg:py-28">
        <div className="container">
          <div className="mx-auto mb-14 max-w-2xl text-center">
            <p className="text-sm font-semibold uppercase tracking-wider text-primary mb-3">
              How it works
            </p>
            <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              Three steps to your perfect route
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              No endless research. No guesswork. Just an honest, debated plan.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3 stagger">
            {steps.map((step) => (
              <div key={step.number} className="relative">
                <div className="mb-4 text-5xl font-extrabold text-primary/15">
                  {step.number}
                </div>
                <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                <p className="text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-y border-border/60 bg-muted/30 py-20 lg:py-28">
        <div className="container">
          <div className="mx-auto mb-14 max-w-2xl text-center">
            <p className="text-sm font-semibold uppercase tracking-wider text-primary mb-3">
              What makes Manzil different
            </p>
            <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              How Manzil thinks
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              A committee of AI specialists debates your trip so you don&apos;t
              have to guess.
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 stagger">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card
                  key={feature.title}
                  className="group relative overflow-hidden border-border/60 bg-card transition-all hover:shadow-md hover:-translate-y-0.5"
                >
                  <CardHeader>
                    <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                      <Icon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-[15px] leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 lg:py-28">
        <div className="container">
          <div className="relative overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-primary via-primary to-primary/80 px-6 py-16 text-center text-primary-foreground shadow-lg">
            <div className="absolute inset-0 bg-grid opacity-10" />
            <div className="relative mx-auto max-w-2xl">
              <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                Ready to find your route?
              </h2>
              <p className="mt-4 text-lg text-primary-foreground/80">
                Tell us about your group, budget, and style. The agents will
                handle the rest.
              </p>
              <Button
                size="lg"
                variant="secondary"
                className="mt-8 group"
                asChild
              >
                <Link href="/plan">
                  Plan my trip
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60 py-10">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <p>Manzil — A multi-agent travel planner for northern Pakistan.</p>
          <p>Built with FastAPI, Next.js, and LangGraph.</p>
        </div>
      </footer>
    </div>
  );
}
