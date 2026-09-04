"use client";

/**
 * India procurement map. Built on react-simple-maps (mature, lightweight SVG
 * choropleth) — no custom GIS. Renders states as a heatmap keyed by procurement
 * activity, animated hotspot markers on the most active states, hover tooltips,
 * and zoom/pan. India is the default and only viewport.
 *
 * TopoJSON is served locally from /geo/india-states.json (public/). It is
 * fetched explicitly before rendering so a missing/failed asset never leaves
 * the map silently blank.
 */
import { AnimatePresence, motion } from "framer-motion";
import { Minus, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup
} from "react-simple-maps";
import { canonicalState, STATE_CENTROIDS } from "@/lib/india";
import { MAP, mapColor } from "@/lib/theme";
import { Button } from "@/components/ui/button";

const GEO_URL = "/geo/india-states.json";

type GeoData = Record<string, unknown>;

export type RegionDatum = {
  region: string;
  tenders: number;
  value: string;
  awards: number;
};

type Hover = { name: string; x: number; y: number; datum?: RegionDatum } | null;

export function IndiaMap({
  regions,
  height = 460,
  onSelectRegion
}: {
  regions: RegionDatum[];
  height?: number;
  onSelectRegion?: (region: string) => void;
}) {
  const [hover, setHover] = useState<Hover>(null);
  const [zoom, setZoom] = useState(1);
  const [geoData, setGeoData] = useState<GeoData | null>(null);
  const [geoError, setGeoError] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(GEO_URL, { cache: "force-cache" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`India map asset returned ${response.status}`);
        return (await response.json()) as GeoData;
      })
      .then((data) => {
        if (alive) setGeoData(data);
      })
      .catch(() => {
        if (alive) setGeoError(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  // Build a lookup keyed by canonical state name.
  const byState = useMemo(() => {
    const map = new Map<string, RegionDatum>();
    for (const r of regions) {
      const key = canonicalState(r.region);
      if (!key) continue;
      const existing = map.get(key);
      if (existing) {
        existing.tenders += r.tenders;
        existing.awards += r.awards;
        existing.value = String(Number(existing.value) + Number(r.value));
      } else {
        map.set(key, { ...r, region: key });
      }
    }
    return map;
  }, [regions]);

  const maxTenders = useMemo(
    () => Math.max(1, ...[...byState.values()].map((r) => r.tenders)),
    [byState]
  );

  // Top active states get an animated hotspot marker.
  const hotspots = useMemo(
    () =>
      [...byState.values()]
        .filter((r) => STATE_CENTROIDS[r.region])
        .sort((a, b) => b.tenders - a.tenders)
        .slice(0, 6),
    [byState]
  );

  function fill(stateName: string): string {
    const datum = byState.get(canonicalState(stateName) ?? "");
    if (!datum || datum.tenders === 0) return MAP.empty;
    return mapColor(datum.tenders / maxTenders);
  }

  return (
    <div className="relative">
      <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-xl border border-border bg-surface/90 backdrop-blur">
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          onClick={() => setZoom((z) => Math.min(z * 1.5, 8))}
          aria-label="Zoom in"
          className="rounded-none text-base"
          icon={<Plus className="h-4 w-4" />}
        />
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          onClick={() => setZoom((z) => Math.max(z / 1.5, 1))}
          aria-label="Zoom out"
          className="rounded-none border-t border-border text-base"
          icon={<Minus className="h-4 w-4" />}
        />
      </div>

      {!geoData && !geoError ? (
        <div className="grid place-items-center text-sm text-faint" style={{ height }}>
          Loading India procurement map…
        </div>
      ) : geoError ? (
        <div className="grid place-items-center rounded-lg border border-border bg-bg-2/30 px-6 text-center" style={{ height }}>
          <div>
            <div className="text-sm font-medium text-text">India map data is temporarily unavailable.</div>
            <div className="mt-1 text-xs text-faint">The underlying procurement records remain available.</div>
          </div>
        </div>
      ) : (
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: 1000, center: [82.8, 22.6] }}
          style={{ width: "100%", height }}
        >
          <ZoomableGroup zoom={zoom} center={[82.8, 22.6]} onMoveEnd={({ zoom: z }) => setZoom(z)} minZoom={1} maxZoom={8}>
            <Geographies geography={geoData}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const name = geo.properties.st_nm ?? geo.properties.NAME_1 ?? geo.properties.name ?? "";
                  const datum = byState.get(canonicalState(name) ?? "");
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      onMouseEnter={(e) => setHover({ name, x: e.clientX, y: e.clientY, datum })}
                      onMouseMove={(e) => setHover((h) => (h ? { ...h, x: e.clientX, y: e.clientY } : h))}
                      onMouseLeave={() => setHover(null)}
                      onClick={() => onSelectRegion?.(canonicalState(name) ?? name)}
                      style={{
                        default: { fill: fill(name), stroke: MAP.stroke, strokeWidth: 0.5, outline: "none", transition: "fill 0.2s" },
                        hover: { fill: MAP.hover, stroke: MAP.stroke, strokeWidth: 0.6, outline: "none", cursor: "pointer" },
                        pressed: { fill: MAP.pressed, outline: "none" }
                      }}
                    />
                  );
                })
              }
            </Geographies>

            {hotspots.map((h) => {
              const c = STATE_CENTROIDS[h.region];
              if (!c) return null;
              return (
                <Marker key={h.region} coordinates={c}>
                  <circle r={4} fill={MAP.marker} stroke={MAP.markerStroke} strokeWidth={1} />
                  <circle r={4} fill="none" stroke={MAP.marker} strokeWidth={1} opacity={0.6}>
                    <animate attributeName="r" from="4" to="16" dur="2.2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.6" to="0" dur="2.2s" repeatCount="indefinite" />
                  </circle>
                </Marker>
              );
            })}
          </ZoomableGroup>
        </ComposableMap>
      )}

      <div className="mt-4 flex items-center gap-3 px-1 text-[11px] text-faint">
        <span>Low</span>
        <div
          className="h-1.5 flex-1 rounded-full"
          style={{
            background: `linear-gradient(90deg, ${[MAP.empty, ...MAP.scale].join(",")})`
          }}
        />
        <span>High</span>
      </div>

      <AnimatePresence>
        {hover?.datum && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.12 }}
            className="pointer-events-none fixed z-50 w-52 rounded-xl border border-border bg-elevated/95 p-3 shadow-2xl backdrop-blur"
            style={{ left: hover.x + 14, top: hover.y + 14 } as React.CSSProperties}
          >
            <div className="text-sm font-semibold text-text">{hover.name}</div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <Stat label="Tenders" value={hover.datum.tenders.toLocaleString("en-IN")} />
              <Stat label="Awards" value={hover.datum.awards.toLocaleString("en-IN")} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-bg-2/60 px-2.5 py-2">
      <div className="t-label">{label}</div>
      <div className="mt-1 font-semibold tabular-nums text-text">{value}</div>
    </div>
  );
}