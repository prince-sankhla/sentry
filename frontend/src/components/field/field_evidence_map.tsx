"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Crosshair, Filter, LocateFixed, MapPin, RefreshCw, ShieldAlert } from "lucide-react";

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";

type Gps = { status?: string; source?: string | null; lat?: number | null; lon?: number | null };
type EventItem = {
  type?: string;
  capability?: string;
  confidence?: number;
  value?: string;
  track_id?: string | null;
  detector?: string;
  mission_id?: string | null;
  requirement_id?: string | null;
  tender_id?: string | null;
  observed_at?: number;
  frame_url?: string | null;
  gps?: Gps;
};

type Status = {
  gps?: Gps;
  recent_events?: EventItem[];
  tender_id?: string | null;
  mission_id?: string | null;
  requirement_id?: string | null;
};

type Flag = EventItem & { id: string; lat: number; lon: number; source: "live" | "saved" };

type LeafletLike = {
  map: (el: HTMLElement, options?: Record<string, unknown>) => any;
  tileLayer: (url: string, options?: Record<string, unknown>) => any;
  divIcon: (options: Record<string, unknown>) => any;
};

type MapInstance = { setView: (center: [number, number], zoom: number) => any; remove: () => void };

declare global {
  interface Window {
    L?: LeafletLike;
  }
}

const typeMeta: Record<string, { label: string; glyph: string; tone: string }> = {
  pothole: { label: "Pothole", glyph: "P", tone: "danger" },
  road_crack: { label: "Road crack", glyph: "C", tone: "warning" },
  streetlight: { label: "Streetlight", glyph: "S", tone: "success" },
  cctv_camera: { label: "CCTV", glyph: "V", tone: "info" },
  signboard: { label: "Signboard", glyph: "G", tone: "info" },
  drain: { label: "Drain / manhole", glyph: "D", tone: "warning" },
  solar_panel: { label: "Solar panel", glyph: "A", tone: "success" },
  evidence: { label: "Field evidence", glyph: "E", tone: "info" },
};

function normalizeType(event: EventItem) {
  const text = `${event.capability || ""} ${event.type || ""}`.toLowerCase().replaceAll(" ", "_");
  if (text.includes("pothole")) return "pothole";
  if (text.includes("crack")) return "road_crack";
  if (text.includes("streetlight") || text.includes("solar_streetlight")) return "streetlight";
  if (text.includes("cctv")) return "cctv_camera";
  if (text.includes("signboard") || text.includes("road_sign")) return "signboard";
  if (text.includes("drain") || text.includes("manhole")) return "drain";
  if (text.includes("solar_panel")) return "solar_panel";
  return "evidence";
}

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      if (window.L) resolve();
      else existing.addEventListener("load", () => resolve(), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Map engine could not be loaded"));
    document.head.appendChild(script);
  });
}

function loadCss() {
  if (document.querySelector(`link[href="${LEAFLET_CSS}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = LEAFLET_CSS;
  document.head.appendChild(link);
}

function stableId(event: EventItem, index: number) {
  return [event.observed_at || 0, event.track_id || "", event.type || "", index].join(":");
}

export function FieldEvidenceMap() {
  const mapEl = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const layersRef = useRef<any[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [status, setStatus] = useState<Status>({});
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [saved, setSaved] = useState<Flag[]>([]);

  const gps = status.gps?.lat != null && status.gps?.lon != null ? status.gps : undefined;

  const liveFlags = useMemo<Flag[]>(() => {
    const next: Flag[] = [];
    let lastGps: Gps | undefined = gps;
    events.slice().reverse().forEach((event, index) => {
      if (event.type === "telemetry" && event.gps?.lat != null && event.gps?.lon != null) {
        lastGps = event.gps;
        return;
      }
      const point = event.gps?.lat != null && event.gps?.lon != null ? event.gps : lastGps;
      if (!point || point.lat == null || point.lon == null) return;
      if (event.type === "dispatch" || event.type === "stop" || event.type === "telemetry") return;
      next.push({ ...event, id: stableId(event, index), lat: point.lat, lon: point.lon, source: "live" });
    });
    return next;
  }, [events, gps]);

  const allFlags = useMemo(() => {
    const byId = new Map<string, Flag>();
    [...saved, ...liveFlags].forEach((flag) => byId.set(flag.id, flag));
    return [...byId.values()].sort((a, b) => (b.observed_at || 0) - (a.observed_at || 0));
  }, [liveFlags, saved]);

  const visibleFlags = useMemo(
    () => filter === "all" ? allFlags : allFlags.filter((flag) => normalizeType(flag) === filter),
    [allFlags, filter],
  );

  const center = useMemo<[number, number]>(() => {
    if (gps?.lat != null && gps?.lon != null) return [gps.lat, gps.lon];
    if (allFlags[0]) return [allFlags[0].lat, allFlags[0].lon];
    return [26.9124, 75.7873];
  }, [allFlags, gps]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("sentry-field-map-flags");
      if (raw) setSaved(JSON.parse(raw) as Flag[]);
    } catch {
      // Ignore malformed local demo cache.
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("sentry-field-map-flags", JSON.stringify(allFlags.filter((flag) => flag.source === "saved")));
    } catch {
      // Browser storage may be unavailable in private mode.
    }
  }, [allFlags]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [statusResponse, eventsResponse] = await Promise.all([
          fetch(`${API}/status`, { cache: "no-store" }),
          fetch(`${API}/events`, { cache: "no-store" }),
        ]);
        if (!statusResponse.ok || !eventsResponse.ok) throw new Error("Field gateway offline");
        const nextStatus = (await statusResponse.json()) as Status;
        const nextEvents = (await eventsResponse.json()) as { events?: EventItem[] };
        if (alive) {
          setStatus(nextStatus);
          setEvents(Array.isArray(nextEvents.events) ? nextEvents.events : []);
        }
      } catch {
        // Map remains available with cached flags when gateway is offline.
      }
    };
    poll();
    const timer = window.setInterval(poll, 1000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let alive = true;
    loadCss();
    loadScript(LEAFLET_JS)
      .then(() => {
        if (!alive || !mapEl.current || !window.L) return;
        mapRef.current = window.L.map(mapEl.current, { zoomControl: false, preferCanvas: true }) as MapInstance;
        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "© OpenStreetMap contributors",
        }).addTo(mapRef.current as any);
        setMapReady(true);
      })
      .catch((reason) => {
        if (alive) setMapError(reason instanceof Error ? reason.message : "Map unavailable");
      });
    return () => {
      alive = false;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !window.L || !mapReady) return;
    mapRef.current.setView(center, gps ? 17 : allFlags.length ? 16 : 13);
  }, [mapReady, center, gps, allFlags.length]);

  useEffect(() => {
    if (!mapRef.current || !window.L || !mapReady) return;
    layersRef.current.forEach((layer) => layer.remove?.());
    layersRef.current = [];
    visibleFlags.forEach((flag) => {
      const kind = normalizeType(flag);
      const meta = typeMeta[kind] || typeMeta.evidence;
      const icon = window.L!.divIcon({
        className: "sentry-map-pin-wrap",
        html: `<div class="sentry-map-pin sentry-map-pin-${meta.tone}"><span>${meta.glyph}</span></div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 32],
        popupAnchor: [0, -31],
      });
      const marker = (window as any).L.marker([flag.lat, flag.lon], { icon }).addTo(mapRef.current as any);
      const confidence = flag.confidence != null ? `${Math.round(flag.confidence * 100)}%` : "—";
      const when = flag.observed_at ? new Date(flag.observed_at * 1000).toLocaleString() : "—";
      const evidence = flag.frame_url ? `<a href="${API}${flag.frame_url}" target="_blank" rel="noreferrer">Open evidence ↗</a>` : "No frame attached";
      marker.bindPopup(`<div class="sentry-map-popup"><div class="sentry-map-popup-kicker">SENTRY FIELD · ${meta.label}</div><strong>${flag.value || meta.label}</strong><div class="sentry-map-popup-grid"><span>Confidence</span><b>${confidence}</b><span>GPS</span><b>${flag.lat.toFixed(5)}, ${flag.lon.toFixed(5)}</b><span>Mission</span><b>${flag.mission_id || status.mission_id || "—"}</b><span>Time</span><b>${when}</b></div><div class="sentry-map-popup-link">${evidence}</div></div>`);
      layersRef.current.push(marker);
    });
  }, [visibleFlags, mapReady, status.mission_id]);

  function saveLiveFlags() {
    setSaved((current) => {
      const existing = new Set(current.map((flag) => flag.id));
      const additions = liveFlags.filter((flag) => !existing.has(flag.id)).map((flag) => ({ ...flag, source: "saved" as const }));
      return [...additions, ...current].slice(0, 500);
    });
  }

  function centerOnGps() {
    if (!mapRef.current || !gps?.lat || !gps?.lon) return;
    mapRef.current.setView([gps.lat, gps.lon], 18);
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      <div className="flex flex-col gap-3 border-b border-border px-4 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-accent"><MapPin className="h-3.5 w-3.5" /> SENTRY FIELD / EVIDENCE MAP</div>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-text">Geospatial findings</h2>
          <p className="mt-1 text-xs text-muted">Every GPS-backed field event can become a persistent investigation flag on the map.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={saveLiveFlags} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text"><ShieldAlert className="mr-1.5 inline h-3.5 w-3.5" /> Save current flags</button>
          <button type="button" onClick={centerOnGps} disabled={!gps} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text disabled:cursor-not-allowed disabled:opacity-40"><LocateFixed className="mr-1.5 inline h-3.5 w-3.5" /> Center GPS</button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-2 px-4 py-3">
        <div className="mr-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[.14em] text-faint"><Filter className="h-3.5 w-3.5" /> Filter</div>
        {["all", "pothole", "road_crack", "streetlight", "cctv_camera", "signboard", "drain", "solar_panel"].map((value) => (
          <button key={value} type="button" onClick={() => setFilter(value)} className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold ${filter === value ? "border-accent bg-accent/10 text-text" : "border-border text-muted"}`}>
            {value === "all" ? "All" : typeMeta[value]?.label || value}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2 text-[10px] uppercase tracking-[.12em] text-faint"><RefreshCw className="h-3.5 w-3.5" /> {visibleFlags.length} mapped</div>
      </div>

      <div className="relative">
        <div ref={mapEl} className="h-[430px] w-full bg-[#eef1f4] md:h-[520px]" />
        {!mapReady && !mapError && <div className="absolute inset-0 grid place-items-center bg-surface/80 text-center"><div><div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" /><div className="mt-3 text-sm font-semibold text-text">Loading field map</div><div className="mt-1 text-xs text-muted">OpenStreetMap tiles · Leaflet</div></div></div>}
        {mapError && <div className="absolute inset-0 grid place-items-center bg-surface/90 text-center"><div><Crosshair className="mx-auto h-8 w-8 text-danger" /><div className="mt-3 text-sm font-semibold text-text">Map engine unavailable</div><div className="mt-1 text-xs text-muted">{mapError}</div></div></div>}
        <div className="pointer-events-none absolute left-4 top-4 flex flex-wrap gap-2">
          <span className="rounded-full border border-border bg-surface/90 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.12em] text-text shadow-sm">{gps ? "GPS LOCK" : "WAITING FOR GPS"}</span>
          <span className="rounded-full border border-border bg-surface/90 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.12em] text-muted shadow-sm">{status.mission_id ? `Mission ${status.mission_id}` : "No active mission"}</span>
        </div>
        <div className="pointer-events-none absolute bottom-4 left-4 right-4 flex flex-wrap items-end justify-between gap-2">
          <div className="rounded-xl border border-border bg-surface/90 px-3 py-2 text-xs shadow-sm backdrop-blur">
            <div className="font-semibold text-text">{gps ? `${gps.lat?.toFixed(5)}, ${gps.lon?.toFixed(5)}` : "GPS coordinates unavailable"}</div>
            <div className="mt-0.5 text-[10px] text-muted">Source: {gps?.source || "Awaiting rover/mobile telemetry"}</div>
          </div>
          <div className="rounded-xl border border-border bg-surface/90 px-3 py-2 text-[10px] text-muted shadow-sm backdrop-blur">
            <span className="font-semibold text-text">{allFlags.length}</span> saved/live flags · <span className="font-semibold text-text">{saved.length}</span> browser-persisted
          </div>
        </div>
      </div>

      <div className="grid gap-3 border-t border-border p-4 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Live GPS</div><div className="mt-1 text-sm font-semibold text-text">{gps ? "Locked" : "Unavailable"}</div><div className="mt-1 text-xs text-muted">No synthetic coordinates are created.</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Current mission</div><div className="mt-1 text-sm font-semibold text-text">{status.mission_id || "—"}</div><div className="mt-1 text-xs text-muted">Tender {status.tender_id || "—"}</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Evidence flags</div><div className="mt-1 text-sm font-semibold text-text">{allFlags.length}</div><div className="mt-1 text-xs text-muted">Click any marker for evidence context.</div></div>
      </div>
    </section>
  );
}
