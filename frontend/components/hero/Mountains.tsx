"use client";

import { useEffect, useRef } from "react";

/**
 * Layered SVG mountain parallax with scroll-driven movement.
 * 3 layers: far (lightest), mid, near (darkest).
 */
export function Mountains() {
  const farRef = useRef<HTMLDivElement>(null);
  const midRef = useRef<HTMLDivElement>(null);
  const nearRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      if (farRef.current) farRef.current.style.transform = `translateY(${y * 0.05}px)`;
      if (midRef.current) midRef.current.style.transform = `translateY(${y * 0.12}px)`;
      if (nearRef.current) nearRef.current.style.transform = `translateY(${y * 0.2}px)`;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Soft gradient sky */}
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(to bottom, #F8F7F4 0%, #F3F1EC 30%, #E8E4DE 60%, #D4CFC7 100%)",
        }}
      />

      {/* Moving gradient overlay */}
      <div
        className="absolute inset-0 opacity-30 animate-gradient"
        style={{
          background: "linear-gradient(120deg, rgba(21,128,61,0.08), rgba(37,99,235,0.08), rgba(217,119,6,0.08))",
        }}
      />

      {/* Far mountains */}
      <div ref={farRef} className="absolute bottom-0 left-0 right-0 transition-transform duration-75">
        <svg width="100%" height="300" viewBox="0 0 1200 300" preserveAspectRatio="none" fill="none">
          <path d="M0 300 L0 180 L150 80 L280 160 L420 60 L580 140 L720 50 L880 120 L1050 70 L1200 150 L1200 300 Z" fill="#C4BFB6" opacity="0.5" />
        </svg>
      </div>

      {/* Mid mountains */}
      <div ref={midRef} className="absolute bottom-0 left-0 right-0 transition-transform duration-75">
        <svg width="100%" height="250" viewBox="0 0 1200 250" preserveAspectRatio="none" fill="none">
          <path d="M0 250 L0 120 L100 40 L250 130 L400 30 L550 110 L700 20 L900 100 L1100 50 L1200 90 L1200 250 Z" fill="#A8A29A" opacity="0.6" />
        </svg>
      </div>

      {/* Near mountains */}
      <div ref={nearRef} className="absolute bottom-0 left-0 right-0 transition-transform duration-75">
        <svg width="100%" height="200" viewBox="0 0 1200 200" preserveAspectRatio="none" fill="none">
          <path d="M0 200 L0 80 L120 20 L300 90 L500 10 L680 80 L860 30 L1060 70 L1200 40 L1200 200 Z" fill="#78716C" opacity="0.7" />
        </svg>
      </div>

      {/* Fog layers */}
      <div className="absolute bottom-0 left-0 right-0 h-40 animate-fog" style={{
        background: "radial-gradient(ellipse at 30% 100%, rgba(255,255,255,0.4) 0%, transparent 60%)",
      }} />
      <div className="absolute bottom-0 left-0 right-0 h-32 animate-fog" style={{
        background: "radial-gradient(ellipse at 70% 100%, rgba(255,255,255,0.3) 0%, transparent 50%)",
        animationDelay: "-15s",
      }} />

      {/* Floating particles */}
      {Array.from({ length: 24 }).map((_, i) => {
        const left = (i * 37) % 100;
        const delay = (i * 0.7) % 8;
        const duration = 8 + (i % 5) * 2;
        return (
          <div
            key={i}
            className="absolute rounded-full bg-white"
            style={{
              left: `${left}%`,
              bottom: `${10 + (i % 6) * 12}%`,
              width: `${2 + (i % 3)}px`,
              height: `${2 + (i % 3)}px`,
              opacity: 0,
              animation: `particle-drift ${duration}s ease-in-out ${delay}s infinite`,
              boxShadow: "0 0 4px rgba(255,255,255,0.8)",
            }}
          />
        );
      })}
    </div>
  );
}
