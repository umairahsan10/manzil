"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, Play, Mountain, Sun, Wind, Shield, Wallet, MapPin } from "lucide-react";
import { PexelsImage } from "@/components/pexels-image";

const destinations = [
  { name: "Hunza Valley", tag: "7,000 m peaks", query: "Hunza Valley autumn Pakistan mountains" },
  { name: "Skardu", tag: "Gateway to K2", query: "Skardu valley Baltistan Pakistan" },
  { name: "Naran Kaghan", tag: "Alpine lakes", query: "Saif ul Malook lake Naran Pakistan" },
  { name: "Fairy Meadows", tag: "Nanga Parbat base", query: "Fairy Meadows Nanga Parbat sunset" },
  { name: "Deosai Plains", tag: "Land of giants", query: "Deosai Plains Sheosar Lake Pakistan" },
  { name: "Passu Cones", tag: "Cathedral peaks", query: "Passu Cones Hunza Pakistan" },
];

const agents = [
  { name: "Weather", icon: Sun, desc: "Forecasts and seasonal windows", color: "bg-amber-500" },
  { name: "Road", icon: MapPin, desc: "Pass status and drive times", color: "bg-stone-500" },
  { name: "Safety", icon: Shield, desc: "Altitude, NOC, and risk flags", color: "bg-rose-500" },
  { name: "Budget", icon: Wallet, desc: "Cost estimates per route", color: "bg-emerald-600" },
  { name: "Local", icon: Wind, desc: "Experience and hidden gems", color: "bg-sky-500" },
];

const steps = [
  {
    number: "01",
    title: "Tell us what you want",
    desc: "Group size, budget, travel style, and how adventurous you want to get.",
  },
  {
    number: "02",
    title: "Five agents debate your route",
    desc: "Each specialist scores independent candidates. No single AI decides.",
  },
  {
    number: "03",
    title: "Get the transparent winner",
    desc: "See the map, the itinerary, the scorecard, and why the runner-ups lost.",
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
    <div
      ref={ref}
      className={`reveal ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="flex flex-col bg-background">
      {/* Hero */}
      <section className="relative min-h-screen overflow-hidden">
        <PexelsImage
          query="Hunza Valley Pakistan mountains dramatic landscape golden hour"
          alt="Northern Pakistan mountains"
          containerClassName="absolute inset-0"
          className="scale-110"
          overlay={
            <>
              <div className="absolute inset-0 bg-gradient-to-r from-background via-background/70 to-transparent" />
              <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background/30" />
              <div className="absolute inset-0 bg-noise" />
            </>
          }
        />

        <div className="container relative z-10 flex min-h-screen flex-col justify-center pt-20 pb-16">
          <div className="max-w-3xl">
            <Reveal>
              <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-background/60 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-muted-foreground backdrop-blur-md">
                <Mountain className="h-3.5 w-3.5 text-primary" />
                AI Travel Planner for Northern Pakistan
              </p>
            </Reveal>

            <Reveal delay={100}>
              <h1 className="text-6xl font-extrabold tracking-tight text-foreground sm:text-7xl md:text-8xl lg:text-9xl">
                Let five
                <span className="block text-primary">guides fight</span>
                <span className="block">for your trip.</span>
              </h1>
            </Reveal>

            <Reveal delay={200}>
              <p className="mt-8 max-w-xl text-lg md:text-xl text-muted-foreground leading-relaxed">
                No more spreadsheet travel planning. Manzil pits Weather, Road,
                Safety, Budget, and Local agents against each other — then shows
                you exactly how the winner was chosen.
              </p>
            </Reveal>

            <Reveal delay={300}>
              <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                <Button
                  size="lg"
                  asChild
                  className="group h-14 rounded-full px-8 text-base bg-foreground text-background hover:bg-foreground/90 shadow-xl"
                >
                  <Link href="/plan">
                    Plan my trip
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </Link>
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  asChild
                  className="h-14 rounded-full px-8 text-base border-foreground/20 bg-background/50 backdrop-blur-sm hover:bg-background"
                >
                  <Link href="/feedback">Share feedback</Link>
                </Button>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Destination filmstrip */}
      <section className="relative border-y border-border bg-secondary/30 py-16 overflow-hidden">
        <div className="absolute inset-0 bg-grain" />
        <div className="container relative mb-8">
          <Reveal>
            <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">
              Destinations
            </p>
            <h2 className="text-3xl font-extrabold sm:text-4xl">
              From Islamabad to the Himalayas
            </h2>
          </Reveal>
        </div>
        <Reveal>
          <div className="flex gap-5 overflow-x-auto px-6 pb-4 pt-2 scrollbar-hide">
            {destinations.map((dest, idx) => (
              <div
                key={dest.name}
                className="group relative aspect-[4/5] w-64 flex-shrink-0 overflow-hidden rounded-3xl shadow-lg transition-transform hover:-translate-y-2"
                style={{ animationDelay: `${idx * 80}ms` }}
              >
                <PexelsImage
                  query={dest.query}
                  alt={dest.name}
                  containerClassName="absolute inset-0"
                  className="transition-transform duration-700 group-hover:scale-110"
                  overlay={
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                  }
                />
                <div className="absolute bottom-0 left-0 right-0 p-6">
                  <p className="text-xs font-bold uppercase tracking-widest text-white/70">
                    {dest.tag}
                  </p>
                  <h3 className="mt-1 text-2xl font-bold text-white">
                    {dest.name}
                  </h3>
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* Agents bento */}
      <section className="py-24 lg:py-32">
        <div className="container">
          <div className="mb-16 max-w-2xl">
            <Reveal>
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">
                The Committee
              </p>
              <h2 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
                Five specialists. One winner.
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Every route is scored by an expert before an orchestrator picks
                the final plan.
              </p>
            </Reveal>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent, idx) => {
              const Icon = agent.icon;
              const isLarge = idx === 0;
              return (
                <Reveal
                  key={agent.name}
                  delay={idx * 80}
                  className={isLarge ? "sm:col-span-2 lg:col-span-1" : ""}
                >
                  <div className="group h-full rounded-3xl border border-border bg-card p-8 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1">
                    <div
                      className={`mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl ${agent.color} text-white shadow-lg`}
                    >
                      <Icon className="h-6 w-6" />
                    </div>
                    <h3 className="text-2xl font-bold">{agent.name}</h3>
                    <p className="mt-2 text-muted-foreground">{agent.desc}</p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* How it works timeline */}
      <section className="relative border-y border-border bg-secondary/30 py-24 lg:py-32">
        <div className="absolute inset-0 bg-grain" />
        <div className="container relative">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <Reveal>
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">
                How it works
              </p>
              <h2 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
                Three steps. Zero guesswork.
              </h2>
            </Reveal>
          </div>

          <div className="relative mx-auto max-w-4xl">
            <div className="absolute left-8 top-0 bottom-0 w-px bg-border md:left-1/2" />
            {steps.map((step, idx) => (
              <Reveal key={step.number} delay={idx * 120}>
                <div
                  className={`relative mb-16 flex items-center gap-8 md:gap-16 ${
                    idx % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
                  }`}
                >
                  <div className="flex-1 md:text-right">
                    <div
                      className={`${idx % 2 === 0 ? "md:pr-8" : "md:pl-8 md:text-left"}`}
                    >
                      <span className="text-6xl font-black text-primary/15">
                        {step.number}
                      </span>
                      <h3 className="text-2xl font-bold -mt-4">{step.title}</h3>
                      <p className="mt-2 text-muted-foreground leading-relaxed">
                        {step.desc}
                      </p>
                    </div>
                  </div>
                  <div className="relative z-10 flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xl font-bold shadow-xl">
                    {step.number}
                  </div>
                  <div className="hidden flex-1 md:block" />
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Stats band */}
      <section className="py-20 lg:py-28">
        <div className="container">
          <div className="grid gap-8 rounded-[2.5rem] border border-border bg-card p-10 shadow-xl md:grid-cols-3">
            {[
              { value: "5", label: "Specialist agents" },
              { value: "3", label: "Routes debated" },
              { value: "100%", label: "Transparent scoring" },
            ].map((stat, idx) => (
              <Reveal key={stat.label} delay={idx * 100}>
                <div className="text-center">
                  <p className="text-5xl font-black text-primary">{stat.value}</p>
                  <p className="mt-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                    {stat.label}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-24 lg:py-32">
        <div className="container">
          <div className="relative overflow-hidden rounded-[2.5rem]">
            <PexelsImage
              query="Karakoram Highway Pakistan mountain road travel"
              alt="Mountain road"
              containerClassName="absolute inset-0"
              className="scale-105"
              overlay={
                <div className="absolute inset-0 bg-gradient-to-br from-primary/95 via-primary/85 to-accent/80" />
              }
            />
            <div className="relative px-8 py-24 text-center md:py-32">
              <Reveal>
                <h2 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl">
                  Ready to find your route?
                </h2>
              </Reveal>
              <Reveal delay={100}>
                <p className="mx-auto mt-4 max-w-xl text-lg text-white/80">
                  Tell us about your group, budget, and style. The agents will
                  handle the rest.
                </p>
              </Reveal>
              <Reveal delay={200}>
                <Button
                  size="lg"
                  className="mt-8 h-14 rounded-full px-8 text-base bg-white text-primary hover:bg-white/90 shadow-xl group"
                  asChild
                >
                  <Link href="/plan">
                    Plan my trip
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </Link>
                </Button>
              </Reveal>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-secondary/30 py-12">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <Mountain className="h-4 w-4 text-primary" />
            <span className="font-bold text-foreground">Manzil</span>
            <span>— Multi-agent travel planner for northern Pakistan</span>
          </div>
          <p>Built with FastAPI, Next.js, and LangGraph.</p>
        </div>
      </footer>
    </div>
  );
}
