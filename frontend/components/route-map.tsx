"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export interface MapStop {
  id: string;
  name: string;
  coords: [number, number];
}

interface RouteMapProps {
  stops: MapStop[];
  height?: string;
  className?: string;
  highlightedStopId?: string | null;
  variant?: "primary" | "alt" | "dashed";
  animated?: boolean;
}

export function RouteMap({
  stops,
  height = "400px",
  className = "",
  highlightedStopId,
  variant = "primary",
  animated = true,
}: RouteMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const routeLayer = useRef<{ source: string; layer: string } | null>(null);

  useEffect(() => {
    if (!mapContainer.current || stops.length === 0) return;

    const bounds = stops.reduce(
      (b, s) => b.extend(s.coords),
      new maplibregl.LngLatBounds(stops[0].coords, stops[0].coords)
    );

    if (!map.current) {
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: {
          version: 8,
          sources: {
            "raster-tiles": {
              type: "raster",
              tiles: [
                "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png",
                "https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png",
                "https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png",
              ],
              tileSize: 256,
              attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            },
          },
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#F8F7F4" },
            },
            {
              id: "tiles",
              type: "raster",
              source: "raster-tiles",
              minzoom: 0,
              maxzoom: 20,
            },
          ],
        },
        center: stops[0].coords,
        zoom: 6,
        interactive: true,
        attributionControl: false,
      });

      map.current.addControl(
        new maplibregl.AttributionControl({ compact: true }),
        "bottom-right"
      );
    }

    const currentMap = map.current;

    const render = () => {
      // Clear existing markers
      markers.current.forEach((m) => m.remove());
      markers.current = [];

      // Remove old route layer/source if exists
      if (routeLayer.current) {
        if (currentMap.getLayer(routeLayer.current.layer)) {
          currentMap.removeLayer(routeLayer.current.layer);
        }
        if (currentMap.getSource(routeLayer.current.source)) {
          currentMap.removeSource(routeLayer.current.source);
        }
        routeLayer.current = null;
      }

      const coords = stops.map((s) => s.coords);
      const sourceId = `route-${variant}`;
      const layerId = `route-line-${variant}`;

      currentMap.addSource(sourceId, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: coords,
          },
        },
      });

      const isPrimary = variant === "primary";
      const lineColor = isPrimary ? "#15803D" : "#D97706";
      const lineWidth = isPrimary ? 5 : 4;
      const lineOpacity = isPrimary ? 0.9 : 0.7;
      const dashPattern = variant === "dashed" ? [2, 2] : undefined;

      currentMap.addLayer({
        id: layerId,
        type: "line",
        source: sourceId,
        layout: {
          "line-join": "round",
          "line-cap": "round",
          ...(dashPattern ? { "line-dasharray": dashPattern } : {}),
        },
        paint: {
          "line-color": lineColor,
          "line-width": lineWidth,
          "line-opacity": lineOpacity,
        },
      });

      // Animated draw effect via dasharray
      if (animated && currentMap.getLayer(layerId)) {
        const steps = 60;
        let frame = 0;
        const dashSeq = [0, 4, 2, 4, 4, 4, 8, 4, 16, 4, 32, 4, 64, 4, 128, 4, 256, 4];
        const animate = () => {
          const idx = Math.min(Math.floor((frame / steps) * (dashSeq.length - 1)), dashSeq.length - 2);
          try {
            currentMap.setPaintProperty(layerId, "line-dasharray", [
              dashSeq[idx],
              dashSeq[idx + 1],
            ]);
          } catch {
            // ignore
          }
          frame++;
          if (frame <= steps) {
            requestAnimationFrame(animate);
          }
        };
        requestAnimationFrame(animate);
      }

      routeLayer.current = { source: sourceId, layer: layerId };

      stops.forEach((stop, idx) => {
        const isHighlighted = highlightedStopId === stop.id;
        const el = document.createElement("div");
        const bg = isPrimary ? "#15803D" : "#D97706";
        el.className = isHighlighted
          ? "flex items-center justify-center rounded-full text-xs font-bold shadow-lg ring-2 ring-white"
          : "flex items-center justify-center rounded-full text-xs font-bold shadow-md border-2 border-white";
        el.style.width = isHighlighted ? "34px" : "28px";
        el.style.height = isHighlighted ? "34px" : "28px";
        el.style.background = bg;
        el.style.color = "#FFFFFF";
        el.style.transition = "all 0.2s ease";
        el.textContent = String(idx + 1);

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat(stop.coords)
          .setPopup(
            new maplibregl.Popup({ offset: 16 }).setHTML(
              `<div style="font-weight:600;font-size:14px">${stop.name}</div>`
            )
          )
          .addTo(currentMap);

        markers.current.push(marker);
      });

      currentMap.fitBounds(bounds, { padding: 80, maxZoom: 10, duration: 1200 });
    };

    if (currentMap.loaded()) {
      render();
    } else {
      currentMap.once("load", render);
    }

    return () => {
      markers.current.forEach((m) => m.remove());
      markers.current = [];
    };
  }, [stops, highlightedStopId, variant, animated]);

  return (
    <div
      ref={mapContainer}
      style={{ height }}
      className={`w-full rounded-2xl overflow-hidden border border-border/60 shadow-inner ${className}`}
    />
  );
}
