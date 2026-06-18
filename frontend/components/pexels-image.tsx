"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { searchImages, ImageSearchResult } from "@/lib/api";

interface PexelsImageProps {
  query: string;
  alt: string;
  className?: string;
  containerClassName?: string;
  fallbackColor?: string;
  overlay?: React.ReactNode;
}

const REQUESTS: Record<string, Promise<ImageSearchResult[]> | undefined> = {};

async function cachedSearch(query: string) {
  if (!REQUESTS[query]) {
    REQUESTS[query] = searchImages(query).catch(() => []);
  }
  return REQUESTS[query]!;
}

export function PexelsImage({
  query,
  alt,
  className,
  containerClassName,
  overlay,
}: PexelsImageProps) {
  const [result, setResult] = useState<ImageSearchResult | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    cachedSearch(query).then((results) => {
      if (!cancelled && results.length > 0) {
        setResult(results[0]);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <div
      className={cn(
        "relative overflow-hidden bg-muted",
        containerClassName
      )}
    >
      {result?.url && (
        <img
          src={result.url}
          alt={alt}
          onLoad={() => setLoaded(true)}
          className={cn(
            "h-full w-full object-cover transition-opacity duration-700",
            loaded ? "opacity-100" : "opacity-0",
            className
          )}
        />
      )}
      {!loaded && (
        <div className="absolute inset-0 animate-pulse bg-muted" />
      )}
      {overlay}
    </div>
  );
}
