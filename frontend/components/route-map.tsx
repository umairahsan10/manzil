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
}

export function RouteMap({
  stops,
  height = "400px",
  className = "",
  highlightedStopId,
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
                "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
                "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
                "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
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
              paint: { "background-color": "#f8fafc" },
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

      currentMap.addSource("route", {
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

      currentMap.addLayer({
        id: "route-line",
        type: "line",
        source: "route",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#0d9488",
          "line-width": 4,
          "line-opacity": 0.85,
        },
      });

      routeLayer.current = { source: "route", layer: "route-line" };

      stops.forEach((stop, idx) => {
        const isHighlighted = highlightedStopId === stop.id;
        const el = document.createElement("div");
        el.className = isHighlighted
          ? "flex items-center justify-center rounded-full bg-accent text-accent-foreground text-xs font-bold shadow-lg ring-2 ring-background"
          : "flex items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold shadow-md border-2 border-background";
        el.style.width = isHighlighted ? "34px" : "28px";
        el.style.height = isHighlighted ? "34px" : "28px";
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

      currentMap.fitBounds(bounds, { padding: 80, maxZoom: 10, duration: 1000 });
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
  }, [stops, highlightedStopId]);

  return (
    <div
      ref={mapContainer}
      style={{ height }}
      className={`w-full rounded-2xl overflow-hidden border border-border/60 shadow-inner ${className}`}
    />
  );
}
