"use client";

/**
 * India procurement map. Built on react-simple-maps (mature, lightweight SVG
 * choropleth) — no custom GIS. Renders states as a heatmap keyed by procurement
 * activity, animated hotspot markers on the most active states, hover tooltips,
 * and zoom/pan. India is the default and only viewport.
 *
 * TopoJSON is served locally from /geo/india-states.json (public/).
 */
import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup
} from "react-simple-maps";
import { canonicalState, STATE_CENTROIDS } from "@/lib/india";

const GEO_URL = "/geo/india-states.json";

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
    if (!datum || datum.tenders === 0) return "#131c28";
    const t = Math.min(1, datum.tenders / maxTenders);
    // charcoal -> gold heat ramp
    return heat(t);
  }

  return (
    <div className="relative">
      <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-lg border border-border bg-surface/90 backdrop-blur">
        <button
          className="grid h-8 w-8 place-items-center text-muted transition hover:bg-surface-2 hover:text-accent"
          onClick={() => setZoom((z) => Math.min(z * 1.5, 8))}
          type="button"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          className="grid h-8 w-8 place-items-center border-t border-border text-muted transition hover:bg-surface-2 hover:text-accent"
          onClick={() => setZoom((z) => Math.max(z / 1.5, 1))}
          type="button"
          aria-label="Zoom out"
        >
          −
        </button>
      </div>

      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 1000, center: [82.8, 22.6] }}
        style={{ width: "100%", height }}
      >
        <ZoomableGroup zoom={zoom} center={[82.8, 22.6]} onMoveEnd={({ zoom: z }) => setZoom(z)} minZoom={1} maxZoom={8}>
          <Geographies geography={GEO_URL}>
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
                      default: { fill: fill(name), stroke: "#0b0f16", strokeWidth: 0.5, outline: "none", transition: "fill 0.2s" },
                      hover: { fill: "#f6c65a", stroke: "#0b0f16", strokeWidth: 0.6, outline: "none", cursor: "pointer" },
                      pressed: { fill: "#e0a73e", outline: "none" }
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
                <circle r={4} fill="#f6c65a" stroke="#080b11" strokeWidth={1} />
                <circle r={4} fill="none" stroke="#f6c65a" strokeWidth={1} opacity={0.6}>
                  <animate attributeName="r" from="4" to="16" dur="2.2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" from="0.6" to="0" dur="2.2s" repeatCount="indefinite" />
                </circle>
              </Marker>
            );
          })}
        </ZoomableGroup>
      </ComposableMap>

      {/* legend */}
      <div className="mt-3 flex items-center gap-3 px-1 text-[11px] text-faint">
        <span>Low</span>
        <div className="h-1.5 flex-1 rounded-full" style={{ background: "linear-gradient(90deg,#131c28,#7a5a24,#e0a73e,#f6c65a)" }} />
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
    <div className="rounded-lg border border-border bg-bg-2/60 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-0.5 font-semibold tabular-nums text-text">{value}</div>
    </div>
  );
}

function heat(t: number): string {
  // interpolate charcoal(#131c28) -> gold(#f6c65a) through amber
  const stops = [
    { at: 0, c: [19, 28, 40] },
    { at: 0.5, c: [122, 90, 36] },
    { at: 1, c: [246, 198, 90] }
  ];
  let lo = stops[0];
  let hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i].at && t <= stops[i + 1].at) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const span = hi.at - lo.at || 1;
  const k = (t - lo.at) / span;
  const c = lo.c.map((v, i) => Math.round(v + (hi.c[i] - v) * k));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
