"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArrowRight, Users, Shield, Wallet, Sun, Mountain } from "lucide-react";
import { Mountains } from "@/components/hero/Mountains";
import { FloatingTripCard } from "@/components/hero/FloatingTripCard";
import { SampleTripsModal } from "@/components/SampleTripsModal";
import type { UserQuery } from "@/lib/types";

const features = [
  {
    icon: Users,
    title: "Personalized for your group",
    desc: "Family, friends, couple, or solo — every route adapts to your group's needs, altitude tolerance, and travel style.",
    color: "text-primary",
    bg: "bg-primary/10",
  },
  {
    icon: Shield,
    title: "Safety-first route intelligence",
    desc: "Altitude profiling, road conditions, hospital proximity, and NOC checks — all analyzed before you leave.",
    color: "text-destructive",
    bg: "bg-destructive/10",
  },
  {
    icon: Wallet,
    title: "Real budget estimation",
    desc: "Transport, lodging, food, activities, and emergency buffer — broken down with realistic PKR costs per segment.",
    color: "text-warning",
    bg: "bg-warning/10",
  },
  {
    icon: Sun,
    title: "Live weather adaptation",
    desc: "Open-Meteo forecasts integrated into route scoring. If the weather shifts, your plan adapts.",
    color: "text-accent",
    bg: "bg-accent/10",
  },
];

const destinations = [
  "Hunza",
  "Skardu",
  "Fairy Meadows",
  "Swat",
  "Naran",
  "Khunjerab",
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
      { threshold: 0.12 }
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
    <div ref={ref} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [showSamples, setShowSamples] = useState(false);

  const handleSampleSelect = (_query: UserQuery) => {
    setShowSamples(false);
    router.push("/plan");
  };

  return (
    <div className="flex flex-col bg-background">
      {/* Hero */}
      <section className="relative min-h-screen overflow-hidden">
        <Mountains />

        <div className="container relative z-10 flex min-h-screen flex-col justify-center pt-20 pb-16">
          <div className="grid lg:grid-cols-[1fr_auto] gap-8 items-center">
            <div className="max-w-2xl">
              <Reveal>
                <p className="mb-6 inline-flex items-center gap-2 rounded-full glass px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  <Mountain className="h-3.5 w-3.5 text-primary" />
                  AI Travel Planner for Northern Pakistan
                </p>
              </Reveal>

              <Reveal delay={100}>
                <h1 className="text-5xl font-display font-bold tracking-tight sm:text-6xl md:text-7xl">
                  Plan smarter.
                  <span className="block text-grad-primary">Travel safer.</span>
                  <span className="block">Explore deeper.</span>
                </h1>
              </Reveal>

              <Reveal delay={200}>
                <p className="mt-8 max-w-xl text-lg md:text-xl text-muted-foreground leading-relaxed">
                  AI-powered travel planning built for Pakistan&apos;s roads, weather, budgets, and people. Five specialist agents debate your best route — transparently.
                </p>
              </Reveal>

              <Reveal delay={300}>
                <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                  <Button
                    size="lg"
                    asChild
                    className="group h-14 rounded-full px-8 text-base bg-primary text-primary-foreground hover:bg-primary/90 shadow-xl shadow-primary/20"
                  >
                    <Link href="/plan">
                      Start Planning
                      <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    onClick={() => setShowSamples(true)}
                    className="h-14 rounded-full px-8 text-base border-border bg-white/50 backdrop-blur-sm hover:bg-white"
                  >
                    Explore Sample Trips
                  </Button>
                </div>
              </Reveal>
            </div>

            {/* Floating trip card */}
            <Reveal delay={400} className="hidden lg:block">
              <FloatingTripCard />
            </Reveal>
          </div>
        </div>
      </section>

      {/* Feature section */}
      <section className="py-24 lg:py-32 relative">
        <div className="container">
          <Reveal>
            <div className="text-center mb-16">
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">
                Why Manzil
              </p>
              <h2 className="text-4xl font-display font-bold tracking-tight sm:text-5xl">
                Intelligence you can trust
              </h2>
            </div>
          </Reveal>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <Reveal key={feature.title} delay={idx * 100}>
                  <div className="group glass-card rounded-3xl p-6 h-full transition-all hover:shadow-xl hover:-translate-y-1 hover:border-glow">
                    <div className={`mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl ${feature.bg} ${feature.color} group-hover:scale-110 transition-transform`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <h3 className="font-display text-lg font-bold mb-2">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{feature.desc}</p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* Social proof + destination chips */}
      <section className="relative py-24 lg:py-32 border-y border-border bg-secondary/30 overflow-hidden">
        <div className="absolute inset-0 bg-grain" />
        <div className="container relative">
          <Reveal>
            <div className="text-center mb-12">
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">
                Built for Pakistani travelers
              </p>
                <h2 className="text-4xl font-display font-bold tracking-tight sm:text-5xl">
                  From the cities to the summits
                </h2>
              {destinations.map((dest, idx) => (
                <button
                  key={dest}
                  onClick={() => router.push("/plan")}
                  className="group inline-flex items-center gap-2 rounded-full glass-card px-6 py-3 text-sm font-bold transition-all hover:scale-105 hover:border-glow"
                  style={{ animationDelay: `${idx * 80}ms` }}
                >
                  <MapPin className="h-4 w-4 text-primary group-hover:scale-110 transition-transform" />
                  {dest}
                </button>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-secondary/30 py-12">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <Mountain className="h-4 w-4 text-primary" />
            <span className="font-bold text-foreground">Manzil</span>
            <span>— Intelligent mountain travel companion for northern Pakistan</span>
          </div>
          <p>Powered by multi-agent AI · FastAPI · Next.js</p>
        </div>
      </footer>

      {/* Sample trips modal */}
      <SampleTripsModal
        open={showSamples}
        onClose={() => setShowSamples(false)}
        onSelect={handleSampleSelect}
      />
    </div>
  );
}

function MapPin({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" fill="currentColor" />
    </svg>
  );
}
