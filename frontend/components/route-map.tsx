"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface MapStop {
  id: string;
  name: string;
  coords: [number, number];
}

interface RouteViewProps {
  stops: MapStop[];
  winner?: boolean;
  height?: string;
}

export function RouteMap({
  stops,
  height = "400px",
}: {
  stops: MapStop[];
  height?: string;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current || stops.length === 0) return;

    const bounds = stops.reduce(
      (b, s) => b.extend(s.coords),
      new maplibregl.LngLatBounds(stops[0].coords, stops[0].coords)
    );

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
    });

    map.current.on("load", () => {
      const coords = stops.map((s) => s.coords);

      map.current?.addSource("route", {
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

      map.current?.addLayer({
        id: "route-line",
        type: "line",
        source: "route",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#0d9488",
          "line-width": 3,
          "line-opacity": 0.7,
        },
      });

      stops.forEach((stop, idx) => {
        const el = document.createElement("div");
        el.className =
          "flex items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold shadow-md border-2 border-background";
        el.style.width = "28px";
        el.style.height = "28px";
        el.textContent = String(idx + 1);

        new maplibregl.Marker({ element: el })
          .setLngLat(stop.coords)
          .setPopup(
            new maplibregl.Popup({ offset: 16 }).setHTML(
              `<div style="font-weight:600;font-size:14px">${stop.name}</div>`
            )
          )
          .addTo(map.current!);
      });

      map.current?.fitBounds(bounds, { padding: 60, maxZoom: 9 });
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [stops]);

  return (
    <div
      ref={mapContainer}
      style={{ height }}
      className="w-full rounded-xl overflow-hidden border border-border/60"
    />
  );
}
