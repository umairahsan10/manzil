"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface PlanningCardProps {
  title: string;
  subtitle: string;
  icon: ReactNode;
  summary: string;
  complete: boolean;
  defaultOpen?: boolean;
  children: ReactNode;
  onToggle?: (open: boolean) => void;
}

export function PlanningCard({
  title,
  subtitle,
  icon,
  summary,
  complete,
  defaultOpen = false,
  children,
  onToggle,
}: PlanningCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    onToggle?.(next);
  };

  return (
    <div
      className={cn(
        "glass-card rounded-3xl overflow-hidden transition-all duration-500",
        open ? "shadow-lg" : "hover:shadow-md",
        complete && !open && "border-glow"
      )}
    >
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-4 p-6 text-left transition-colors hover:bg-white/40"
      >
        <div
          className={cn(
            "flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl transition-all",
            complete
              ? "bg-primary text-primary-foreground"
              : open
                ? "bg-accent text-accent-foreground"
                : "bg-secondary text-muted-foreground"
          )}
        >
          {complete && !open ? <Check className="h-5 w-5" /> : icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-display text-lg font-semibold tracking-tight">{title}</h3>
            {complete && (
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
                Done
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground truncate mt-0.5">
            {open ? subtitle : summary}
          </p>
        </div>

        <ChevronDown
          className={cn(
            "h-5 w-5 text-muted-foreground transition-transform duration-300 shrink-0",
            open && "rotate-180"
          )}
        />
      </button>

      <div
        className={cn(
          "grid transition-all duration-500 ease-in-out",
          open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        )}
      >
        <div className="overflow-hidden">
          <div className="px-6 pb-6 pt-2">
            <div className="h-px bg-border/60 mb-6" />
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
