"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Crosshair, Filter, LocateFixed, MapPin, RefreshCw, ShieldAlert, Navigation } from "lucide-react";

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
  tender_id?: string | null;
  mission_id?: string | null;
  requirement_id?: string | null;
};
type Flag = EventItem & { id: string; lat: number; lon: number; source: "live" | "saved" };
type LeafletLike = {
  map: (el: HTMLElement, options?: Record<string, unknown>) => any;
  tileLayer: (url: string, options?: Record<string, unknown>) => any;
  divIcon: (options: Record<string, unknown>) => any;
  marker: (latlng: [number, number], options?: Record<string, unknown>) => any;
  polyline?: (latlngs: [number, number][], options?: Record<string, unknown>) => any;
  control?: { zoom: (options?: Record<string, unknown>) => { addTo: (map: any) => any } };
};
type MapInstance = {
  setView: (center: [number, number], zoom: number) => any;
  getZoom?: () => number;
  remove: () => void;
};

declare global { interface Window { L?: LeafletLike } }

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
  if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = LEAFLET_CSS;
    document.head.appendChild(link);
  }
  if (!document.querySelector("style[data-sentry-map]")) {
    const style = document.createElement("style");
    style.dataset.sentryMap = "true";
    style.textContent = `
      .sentry-map-pin-wrap{background:transparent!important;border:0!important}
      .sentry-map-pin{width:34px;height:34px;border-radius:999px 999px 999px 4px;transform:rotate(-45deg);display:grid;place-items:center;border:2px solid rgba(255,255,255,.92);box-shadow:0 6px 18px rgba(0,0,0,.28)}
      .sentry-map-pin span{transform:rotate(45deg);font:800 13px/1 ui-monospace,monospace;color:#fff}
      .sentry-map-pin-danger{background:#dc2626}.sentry-map-pin-warning{background:#d97706}.sentry-map-pin-success{background:#059669}.sentry-map-pin-info{background:#2563eb}
      .sentry-rover-wrap{background:transparent!important;border:0!important}
      .sentry-rover{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;background:#0ea5e9;border:3px solid #fff;box-shadow:0 0 0 7px rgba(14,165,233,.18),0 7px 22px rgba(0,0,0,.30);animation:sentryPulse 1.8s ease-out infinite}
      .sentry-rover span{font:900 15px/1 ui-sans-serif,system-ui;color:#fff}
      .sentry-rover-live{font:800 10px/1 ui-monospace,monospace;color:#0369a1;background:#e0f2fe;border:1px solid rgba(3,105,161,.2);border-radius:999px;padding:5px 8px;box-shadow:0 4px 14px rgba(0,0,0,.12)}
      @keyframes sentryPulse{0%{box-shadow:0 0 0 0 rgba(14,165,233,.40),0 7px 22px rgba(0,0,0,.30)}70%{box-shadow:0 0 0 15px rgba(14,165,233,0),0 7px 22px rgba(0,0,0,.30)}100%{box-shadow:0 0 0 0 rgba(14,165,233,0),0 7px 22px rgba(0,0,0,.30)}}
      .sentry-map-popup{min-width:230px;font:12px/1.45 ui-sans-serif,system-ui}.sentry-map-popup-kicker{font:700 10px/1.2 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;color:#667085;margin-bottom:5px}.sentry-map-popup strong{font-size:14px}.sentry-map-popup-grid{display:grid;grid-template-columns:1fr auto;gap:5px 10px;margin-top:9px}.sentry-map-popup-grid span{color:#667085}.sentry-map-popup-grid b{text-align:right}.sentry-map-popup-link{margin-top:10px;padding-top:8px;border-top:1px solid #e5e7eb}.sentry-map-popup-link a{font-weight:700;color:#2563eb}.leaflet-control-zoom a{font-weight:700}
    `;
    document.head.appendChild(style);
  }
}

function stableId(event: EventItem, index: number) {
  return [event.observed_at || 0, event.track_id || "", event.type || "", event.value || "", index].join(":");
}

export function FieldEvidenceMap() {
  const mapEl = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const layersRef = useRef<any[]>([]);
  const roverLayerRef = useRef<any | null>(null);
  const trailLayerRef = useRef<any | null>(null);
  const firstGpsFitRef = useRef(false);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [status, setStatus] = useState<Status>({});
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [saved, setSaved] = useState<Flag[]>([]);
  const [saveState, setSaveState] = useState("Auto-save ON");

  const gps = status.gps?.lat != null && status.gps?.lon != null ? status.gps : undefined;

  const liveFlags = useMemo<Flag[]>(() => {
    const next: Flag[] = [];
    let lastGps: Gps | undefined = gps;
    events.slice().reverse().forEach((event, index) => {
      if (event.type === "telemetry" && event.gps?.lat != null && event.gps?.lon != null) {
        lastGps = event.gps;
        return;
      }
      if (["dispatch", "stop", "telemetry"].includes(event.type || "")) return;
      const point = event.gps?.lat != null && event.gps?.lon != null ? event.gps : lastGps;
      if (!point || point.lat == null || point.lon == null) return;
      next.push({ ...event, id: stableId(event, index), lat: point.lat, lon: point.lon, source: "live" });
    });
    return next;
  }, [events, gps]);

  const allFlags = useMemo(() => {
    const byId = new Map<string, Flag>();
    [...saved, ...liveFlags].forEach((flag) => byId.set(flag.id, flag));
    return [...byId.values()].sort((a, b) => (b.observed_at || 0) - (a.observed_at || 0));
  }, [liveFlags, saved]);

  const visibleFlags = useMemo(() => filter === "all" ? allFlags : allFlags.filter((flag) => normalizeType(flag) === filter), [allFlags, filter]);

  const route = useMemo<[number, number][]>(() => {
    return events
      .filter((event) => event.type === "telemetry" && event.gps?.lat != null && event.gps?.lon != null)
      .slice()
      .reverse()
      .map((event) => [event.gps!.lat!, event.gps!.lon!]);
  }, [events]);

  useEffect(() => {
    let alive = true;
    fetch("/api/field-map", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => { if (alive && Array.isArray(data?.flags)) setSaved(data.flags as Flag[]); })
      .catch(() => {
        try {
          const raw = window.localStorage.getItem("sentry-field-map-flags");
          if (raw && alive) setSaved(JSON.parse(raw) as Flag[]);
        } catch {}
      });
    return () => { alive = false; };
  }, []);

  useEffect(() => { try { window.localStorage.setItem("sentry-field-map-flags", JSON.stringify(saved)); } catch {} }, [saved]);

  useEffect(() => {
    if (!liveFlags.length) return;
    const additions = liveFlags.filter((flag) => !saved.some((item) => item.id === flag.id));
    if (!additions.length) return;
    const next = [...additions.map((flag) => ({ ...flag, source: "saved" as const })), ...saved].slice(0, 500);
    setSaved(next);
    setSaveState(`Auto-saved ${next.length} flags`);
    const timer = window.setTimeout(() => setSaveState("Auto-save ON"), 1800);
    void fetch("/api/field-map", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ flags: next }),
    }).catch(() => {
      try { window.localStorage.setItem("sentry-field-map-flags", JSON.stringify(next)); } catch {}
      setSaveState("Local fallback saved");
    });
    return () => window.clearTimeout(timer);
  }, [liveFlags, saved]);

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
        if (alive) { setStatus(nextStatus); setEvents(Array.isArray(nextEvents.events) ? nextEvents.events : []); }
      } catch {}
    };
    poll();
    const timer = window.setInterval(poll, 1000);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    let alive = true;
    loadCss();
    loadScript(LEAFLET_JS).then(() => {
      if (!alive || !mapEl.current || !window.L) return;
      mapRef.current = window.L.map(mapEl.current, { zoomControl: false, minZoom: 3, maxZoom: 19, preferCanvas: true }) as MapInstance;
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap contributors" }).addTo(mapRef.current as any);
      window.L.control?.zoom({ position: "bottomright" }).addTo(mapRef.current as any);
      mapRef.current.setView([20, 0], 3);
      setMapReady(true);
    }).catch((reason) => { if (alive) setMapError(reason instanceof Error ? reason.message : "Map unavailable"); });
    return () => {
      alive = false;
      roverLayerRef.current?.remove?.();
      trailLayerRef.current?.remove?.();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !window.L || !mapReady || !gps) return;
    const point: [number, number] = [gps.lat!, gps.lon!];
    const roverIcon = window.L.divIcon({ className: "sentry-rover-wrap", html: `<div class="sentry-rover"><span>R</span></div>`, iconSize: [42, 42], iconAnchor: [21, 21], popupAnchor: [0, -18] });
    if (!roverLayerRef.current) {
      roverLayerRef.current = window.L.marker(point, { icon: roverIcon, zIndexOffset: 1000 }).addTo(mapRef.current as any);
      roverLayerRef.current.bindPopup(`<div class="sentry-map-popup"><div class="sentry-map-popup-kicker">SENTRY FIELD · LIVE MACHINE</div><strong>Rover live location</strong><div class="sentry-map-popup-grid"><span>GPS</span><b>${gps.lat!.toFixed(5)}, ${gps.lon!.toFixed(5)}</b><span>Source</span><b>${gps.source || "telemetry"}</b><span>Mission</span><b>${status.mission_id || "—"}</b></div></div>`);
    } else {
      roverLayerRef.current.setLatLng?.(point);
    }
    if (!firstGpsFitRef.current) {
      firstGpsFitRef.current = true;
      mapRef.current.setView(point, Math.max(15, mapRef.current.getZoom?.() || 15));
    }
  }, [gps?.lat, gps?.lon, mapReady, status.mission_id]);

  useEffect(() => {
    if (!mapRef.current || !window.L || !mapReady) return;
    trailLayerRef.current?.remove?.();
    trailLayerRef.current = null;
    if (route.length >= 2 && window.L.polyline) {
      trailLayerRef.current = window.L.polyline(route, { weight: 4, opacity: 0.72, lineCap: "round", lineJoin: "round" }).addTo(mapRef.current as any);
    }
  }, [route, mapReady]);

  useEffect(() => {
    if (!mapRef.current || !window.L || !mapReady) return;
    layersRef.current.forEach((layer) => layer.remove?.());
    layersRef.current = [];
    visibleFlags.forEach((flag) => {
      const kind = normalizeType(flag);
      const meta = typeMeta[kind] || typeMeta.evidence;
      const icon = window.L!.divIcon({ className: "sentry-map-pin-wrap", html: `<div class="sentry-map-pin sentry-map-pin-${meta.tone}"><span>${meta.glyph}</span></div>`, iconSize: [34, 34], iconAnchor: [17, 31], popupAnchor: [0, -28] });
      const marker = window.L!.marker([flag.lat, flag.lon], { icon }).addTo(mapRef.current as any);
      const confidence = flag.confidence != null ? `${Math.round(flag.confidence * 100)}%` : "—";
      const when = flag.observed_at ? new Date(flag.observed_at * 1000).toLocaleString() : "—";
      const evidence = flag.frame_url ? `<a href="${API}${flag.frame_url}" target="_blank" rel="noreferrer">Open evidence ↗</a>` : "No frame attached";
      marker.bindPopup(`<div class="sentry-map-popup"><div class="sentry-map-popup-kicker">SENTRY FIELD · ${meta.label}</div><strong>${flag.value || meta.label}</strong><div class="sentry-map-popup-grid"><span>Confidence</span><b>${confidence}</b><span>GPS</span><b>${flag.lat.toFixed(5)}, ${flag.lon.toFixed(5)}</b><span>Mission</span><b>${flag.mission_id || status.mission_id || "—"}</b><span>Requirement</span><b>${flag.requirement_id || status.requirement_id || "—"}</b><span>Time</span><b>${when}</b></div><div class="sentry-map-popup-link">${evidence}</div></div>`);
      layersRef.current.push(marker);
    });
  }, [visibleFlags, mapReady, status.mission_id, status.requirement_id]);

  function centerOnGps() {
    if (!mapRef.current || gps?.lat == null || gps?.lon == null) return;
    mapRef.current.setView([gps.lat, gps.lon], 18);
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
      <div className="flex flex-col gap-3 border-b border-border px-4 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-accent"><MapPin className="h-3.5 w-3.5" /> SENTRY FIELD / EVIDENCE MAP</div>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-text">Geospatial findings</h2>
          <p className="mt-1 text-xs text-muted">Live rover position, inspection route and GPS-backed evidence on one map.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-[11px] font-semibold text-muted">{saveState}</span>
          <button type="button" onClick={centerOnGps} disabled={!gps} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text disabled:cursor-not-allowed disabled:opacity-40"><LocateFixed className="mr-1.5 inline h-3.5 w-3.5" /> Center rover</button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-2 px-4 py-3">
        <div className="mr-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[.14em] text-faint"><Filter className="h-3.5 w-3.5" /> Filter</div>
        {["all", "pothole", "road_crack", "streetlight", "cctv_camera", "signboard", "drain", "solar_panel"].map((value) => (
          <button key={value} type="button" onClick={() => setFilter(value)} className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold ${filter === value ? "border-accent bg-accent/10 text-text" : "border-border text-muted"}`}>
            {value === "all" ? "All" : typeMeta[value]?.label || value}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-3 text-[10px] uppercase tracking-[.12em] text-faint"><span className="inline-flex items-center gap-1.5"><Navigation className="h-3.5 w-3.5" /> {route.length} GPS points</span><span className="inline-flex items-center gap-1.5"><RefreshCw className="h-3.5 w-3.5" /> {visibleFlags.length} flags</span></div>
      </div>

      <div className="relative">
        <div ref={mapEl} className="h-[430px] w-full bg-[#eef1f4] md:h-[560px]" />
        {!mapReady && !mapError && <div className="absolute inset-0 grid place-items-center bg-surface/80 text-center"><div><div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" /><div className="mt-3 text-sm font-semibold text-text">Loading field map</div><div className="mt-1 text-xs text-muted">OpenStreetMap · Leaflet · live evidence layer</div></div></div>}
        {mapError && <div className="absolute inset-0 grid place-items-center bg-surface/90 text-center"><div><Crosshair className="mx-auto h-8 w-8 text-danger" /><div className="mt-3 text-sm font-semibold text-text">Map engine unavailable</div><div className="mt-1 text-xs text-muted">{mapError}</div></div></div>}
        <div className="pointer-events-none absolute left-4 top-4 flex flex-wrap gap-2">
          <span className={`rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.14em] ${gps ? "border-accent/30 bg-accent/10 text-text" : "border-border bg-surface/85 text-muted"}`}>{gps ? "● Rover GPS live" : "○ Rover GPS unavailable"}</span>
          {route.length >= 2 && <span className="rounded-full border border-border bg-surface/85 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.14em] text-muted">Route tracked</span>}
        </div>
        {gps && <div className="pointer-events-none absolute right-4 bottom-4"><span className="sentry-rover-live">ROVER LIVE · {gps.lat.toFixed(5)}, {gps.lon.toFixed(5)}</span></div>}
      </div>
    </section>
  );
}
