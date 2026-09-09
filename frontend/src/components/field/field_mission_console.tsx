"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Camera, CheckCircle2, FileText, Gauge, MapPin, Navigation, Radar, Siren, ShieldCheck, Wifi, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/page";

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type Tender = { id: string; tender_id: string; reference_number: string; title: string; source_name: string; source_url: string; source_verified_on?: string; contract_location: string; category: string; machine: string; demo_site: string; requirements: Requirement[]; verification_notes: string };
type Gps = { status?: string; source?: string | null; lat?: number | null; lon?: number | null; accuracy_m?: number | null; captured_at?: number | null };
type EventItem = { type: string; capability?: string; observation?: string; confidence?: number; value?: string; track_id?: string | null; detector?: string; mission_id?: string | null; requirement_id?: string | null; tender_id?: string | null; machine_id?: string | null; observed_at?: number; frame_url?: string | null; gps?: Gps };
type Status = { running: boolean; authorized: boolean; camera_url: string; fps: number; inference_ms: number; findings: number; evidence: number; last_detection: { type: string; confidence: number; track_id?: string | null } | null; last_identity: string | null; last_error: string | null; mission_id: string | null; requirement_id: string | null; tender_id: string | null; capabilities: string[]; confidence: number; every_n_frames: number; machine: string | null; demo_site: string | null; dispatch_at: number | null; machine_id: string | null; battery: number | null; speed: number | null; gps: Gps; recent_events: EventItem[] };

const EMPTY: Status = { running: false, authorized: false, camera_url: DEFAULT_CAMERA, fps: 0, inference_ms: 0, findings: 0, evidence: 0, last_detection: null, last_identity: null, last_error: null, mission_id: null, requirement_id: null, tender_id: null, capabilities: [], confidence: 0.55, every_n_frames: 1, machine: null, demo_site: null, dispatch_at: null, machine_id: null, battery: null, speed: null, gps: { status: "unavailable", source: null, lat: null, lon: null }, recent_events: [] };
const LABELS: Record<string, string> = { pothole: "Pothole", road_crack: "Road crack", streetlight: "Streetlight", cctv_camera: "CCTV", signboard: "Signboard", drain: "Drain / manhole", solar_panel: "Solar panel", asset_qr: "QR / asset ID", asset_text: "OCR / asset text" };
function evidenceUrl(url: string | null | undefined) { return url ? (url.startsWith("http") ? url : `${API}${url}`) : null; }

export function FieldMissionConsole({ tenderKey, requirementId }: { tenderKey?: string; requirementId?: string }) {
  const [tender, setTender] = useState<Tender | null>(null);
  const [primaryRequirement, setPrimaryRequirement] = useState<Requirement | null>(null);
  const [status, setStatus] = useState<Status>(EMPTY);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [confidence, setConfidence] = useState(0.55);
  const [everyNFrames, setEveryNFrames] = useState(1);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const [gpsWatching, setGpsWatching] = useState(false);
  const [tab, setTab] = useState<"live" | "evidence">("live");
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);

  const capabilities = useMemo(() => { const seen = new Set<string>(); return (tender?.requirements || []).map((r) => r.capability).filter((value) => { if (!value || seen.has(value)) return false; seen.add(value); return true; }); }, [tender]);
  const evidenceEvents = useMemo(() => events.filter((e) => e.type === "evidence" && e.frame_url), [events]);
  const gpsLive = status.gps?.status === "live" && status.gps.lat != null && status.gps.lon != null;
  const active = Boolean(streamUrl && status.running);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const url = tenderKey ? `${API}/tenders/${encodeURIComponent(tenderKey)}` : `${API}/tenders`;
        const response = await fetch(url, { cache: "no-store" }); if (!response.ok) throw new Error("Field tender could not be resolved");
        const payload = await response.json(); const resolved = tenderKey ? payload as Tender : (Array.isArray(payload?.tenders) ? payload.tenders[0] : null);
        if (!resolved) throw new Error("No field investigation target is available");
        const requirement = resolved.requirements.find((item: Requirement) => item.id === requirementId) ?? resolved.requirements[0] ?? null;
        if (!requirement) throw new Error("Selected field tender has no inspection requirements");
        if (alive) { setTender(resolved as Tender); setPrimaryRequirement(requirement); setError(null); }
      } catch (reason) { if (alive) setError(reason instanceof Error ? reason.message : "Field handoff unavailable"); }
    };
    void load(); return () => { alive = false; };
  }, [requirementId, tenderKey]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [healthResponse, statusResponse, eventsResponse] = await Promise.all([fetch(`${API}/health`, { cache: "no-store" }), fetch(`${API}/status`, { cache: "no-store" }), fetch(`${API}/events`, { cache: "no-store" })]);
        if (!statusResponse.ok || !eventsResponse.ok) throw new Error();
        const nextStatus = await statusResponse.json() as Status; const nextEvents = await eventsResponse.json() as { events?: EventItem[] };
        if (alive) { setOnline(healthResponse.ok); setStatus(nextStatus); setEvents(Array.isArray(nextEvents.events) ? nextEvents.events : []); }
      } catch { if (alive) setOnline(false); }
    };
    void poll(); const timer = window.setInterval(() => void poll(), 700); return () => { alive = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => () => { if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current); }, []);
  function stopGps() { if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current); watchId.current = null; setGpsWatching(false); }
  function startGps(missionId: string) {
    if (!("geolocation" in navigator) || !tender || !primaryRequirement) return; stopGps();
    const deviceId = `browser-gps:${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    watchId.current = navigator.geolocation.watchPosition(async (position) => {
      try { await fetch(`${API}/telemetry/mobile`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tender_id: tender.id, mission_id: missionId, requirement_id: primaryRequirement.id, machine_id: deviceId, lat: position.coords.latitude, lon: position.coords.longitude, accuracy_m: position.coords.accuracy, captured_at: position.timestamp, speed: position.coords.speed }) }); } catch { /* rover telemetry can provide GPS too */ }
    }, () => setGpsWatching(false), { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 });
    setGpsWatching(true);
  }

  async function startMission() {
    if (!tender || !primaryRequirement || !capabilities.length) return setError("SENTRY could not derive a field inspection plan from this investigation.");
    if (!camera.trim()) return setError("Camera URL is required."); setError(null);
    try {
      const missionId = `${tender.id}-${primaryRequirement.id}-${Date.now()}`;
      const dispatch = await fetch(`${API}/dispatch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tender_id: tender.id, mission_id: missionId, requirement_id: primaryRequirement.id, capability: primaryRequirement.capability, capabilities, machine: tender.machine, demo_site: tender.demo_site }) });
      const payload = await dispatch.json().catch(() => ({})); if (!dispatch.ok) throw new Error(payload.detail || "Rover dispatch was rejected");
      startGps(missionId);
      const query = new URLSearchParams({ camera_url: camera.trim(), confidence: String(confidence), every_n_frames: String(everyNFrames), mission_id: missionId, requirement_id: primaryRequirement.id, capabilities: capabilities.join(","), t: String(Date.now()) });
      setStreamUrl(`${API}/stream?${query.toString()}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Field mission could not start"); }
  }
  async function stopMission() { try { await fetch(`${API}/stop`, { method: "POST" }); } finally { setStreamUrl(null); stopGps(); setStatus((s) => ({ ...s, running: false, authorized: false })); } }

  if (!tender || !primaryRequirement) return <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm"><div className="flex items-center gap-2 text-sm text-muted">{error ? <XCircle className="h-4 w-4 text-danger" /> : <Activity className="h-4 w-4 animate-pulse text-accent" />}{error || "Resolving exact investigation → field mission plan…"}</div></section>;

  return <main className="mx-auto w-full max-w-[1900px] space-y-5">
    <section className="rounded-2xl border border-accent/20 bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between"><div><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / LIVE VERIFICATION</div><h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">Autonomous field mission control</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted">The investigation defines the inspection requirements. SENTRY selects matching vision capabilities automatically and binds detections, frames and GPS to one mission.</p></div><div className="flex flex-wrap items-center gap-2"><Badge tone={online ? "success" : "muted"}><Wifi className="mr-1 inline h-3 w-3" />{online ? "Gateway online" : "Gateway offline"}</Badge><Badge tone={gpsLive ? "success" : "muted"}><Navigation className="mr-1 inline h-3 w-3" />{gpsLive ? "GPS live" : gpsWatching ? "GPS waiting" : "GPS idle"}</Badge>{active ? <button type="button" onClick={() => void stopMission()} className="inline-flex items-center gap-2 rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-xs font-semibold text-danger"><Siren className="h-3.5 w-3.5" /> Stop mission</button> : <button type="button" onClick={() => void startMission()} disabled={!online} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-40"><ShieldCheck className="h-3.5 w-3.5" /> Start SENTRY FIELD</button>}</div></div>
      <div className="mt-5 grid gap-3 lg:grid-cols-[1.6fr_1fr_1fr]"><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Investigation target</div><div className="mt-1 text-sm font-semibold text-text">{tender.title}</div><div className="mt-1 text-xs text-muted">{tender.reference_number} · {tender.contract_location}</div></div><div className="rounded-xl border border-accent/20 bg-accent/5 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-accent">Primary requirement</div><div className="mt-1 text-sm font-semibold text-text">{primaryRequirement.label}</div><div className="mt-1 text-xs text-muted">{primaryRequirement.id} · expected {primaryRequirement.expected_quantity}</div></div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Machine / site</div><div className="mt-1 text-sm font-semibold text-text">{tender.machine}</div><div className="mt-1 text-xs text-muted">{tender.demo_site}</div></div></div>
      <div className="mt-4 rounded-xl border border-accent/20 bg-accent/5 p-4"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.15em] text-accent"><Radar className="h-3.5 w-3.5" /> Auto-selected SENTRY capabilities</div><div className="mt-3 flex flex-wrap gap-2">{capabilities.map((capability) => <span key={capability} className="rounded-full border border-accent/25 bg-accent/10 px-3 py-1.5 text-[11px] font-semibold text-text">{LABELS[capability] || capability}</span>)}</div><div className="mt-2 text-[11px] text-muted">No manual detector selection is required.</div></div>
      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_160px_160px]"><label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Camera source</span><input value={camera} onChange={(e) => setCamera(e.target.value)} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50" /></label><label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Confidence</span><input type="number" min="0.05" max="0.99" step="0.01" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none" /></label><label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Frame cadence</span><input type="number" min="1" max="60" value={everyNFrames} onChange={(e) => setEveryNFrames(Math.max(1, Number(e.target.value)))} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none" /></label></div>
      {error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2.5 text-xs text-danger">{error}</div>}{status.last_error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2.5 text-xs text-danger">Gateway: {status.last_error}</div>}
    </section>
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6"><div className="rounded-2xl border border-border bg-surface p-4"><Activity className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">State</div><div className="mt-2 text-2xl font-semibold text-text">{active ? "LIVE" : status.authorized ? "READY" : "IDLE"}</div></div><div className="rounded-2xl border border-border bg-surface p-4"><Gauge className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">FPS</div><div className="mt-2 text-2xl font-semibold text-text">{status.fps.toFixed(1)}</div></div><div className="rounded-2xl border border-border bg-surface p-4"><Gauge className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Inference</div><div className="mt-2 text-2xl font-semibold text-text">{status.inference_ms.toFixed(0)} ms</div></div><div className="rounded-2xl border border-border bg-surface p-4"><Radar className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Findings</div><div className="mt-2 text-2xl font-semibold text-text">{status.findings}</div></div><div className="rounded-2xl border border-border bg-surface p-4"><FileText className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Evidence</div><div className="mt-2 text-2xl font-semibold text-text">{status.evidence}</div></div><div className="rounded-2xl border border-border bg-surface p-4"><MapPin className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">GPS</div><div className="mt-2 text-sm font-semibold text-text">{gpsLive ? `${status.gps.lat!.toFixed(5)}, ${status.gps.lon!.toFixed(5)}` : "Waiting"}</div></div></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div className="flex gap-1 rounded-lg bg-surface-2 p-1"><button type="button" onClick={() => setTab("live")} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${tab === "live" ? "bg-surface text-text" : "text-muted"}`}>Live camera</button><button type="button" onClick={() => setTab("evidence")} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${tab === "evidence" ? "bg-surface text-text" : "text-muted"}`}>Evidence ({evidenceEvents.length})</button></div><div className="text-[10px] uppercase tracking-[.14em] text-faint">Mission {status.mission_id || "—"}</div></div>{tab === "live" ? <div className="p-3"><div className="relative min-h-[55vh] overflow-hidden rounded-xl bg-[#0b0e13]">{streamUrl ? <img src={streamUrl} alt="SENTRY FIELD live annotated camera" className="h-full w-full object-contain" onError={() => setError("Live gateway stream failed. Check camera URL and gateway logs.")} /> : <div className="absolute inset-0 grid place-items-center text-center"><div><Camera className="mx-auto h-10 w-10 text-accent" /><div className="mt-3 text-sm font-semibold text-text">SENTRY FIELD is ready</div><div className="mt-1 text-xs text-muted">Start the mission and the annotated live camera stream will appear here.</div></div></div>}<div className="absolute left-4 top-4 flex flex-wrap gap-2"><Badge tone={active ? "success" : "muted"}>{active ? "LIVE" : "IDLE"}</Badge>{status.last_detection && <Badge tone="success">{status.last_detection.type} · {Math.round(status.last_detection.confidence * 100)}%</Badge>}</div><div className="absolute bottom-4 left-4 flex flex-wrap gap-2"><Badge tone="muted">GPS {status.gps.status || "unavailable"}</Badge>{status.machine_id && <Badge tone="muted">{status.machine_id}</Badge>}</div></div></div> : <div className="divide-y divide-border">{evidenceEvents.length ? evidenceEvents.slice(0, 50).map((event, index) => { const url = evidenceUrl(event.frame_url); return <div key={`${event.observed_at || 0}-${event.track_id || index}`} className="grid gap-4 p-4 md:grid-cols-[180px_1fr_auto] md:items-center"><div className="aspect-video overflow-hidden rounded-xl border border-border bg-surface-2">{url ? <a href={url} target="_blank" rel="noreferrer"><img src={url} alt="Captured SENTRY FIELD evidence" className="h-full w-full object-cover" /></a> : <div className="grid h-full place-items-center"><FileText className="h-5 w-5 text-accent" /></div>}</div><div><div className="text-sm font-semibold text-text">{event.capability || event.type || "Field evidence"}</div><div className="mt-1 text-xs text-muted">{event.observation || event.value || `Detector: ${event.detector || "vision"}`}</div><div className="mt-1 text-xs text-faint">{event.confidence != null ? `Confidence ${Math.round(event.confidence * 100)}%` : ""}{event.track_id ? ` · ${event.track_id}` : ""}</div>{event.gps?.lat != null && event.gps?.lon != null && <div className="mt-1 text-xs text-faint">GPS {event.gps.lat.toFixed(6)}, {event.gps.lon.toFixed(6)}</div>}</div><Badge tone="success"><CheckCircle2 className="mr-1 inline h-3 w-3" />Captured</Badge></div>; }) : <div className="p-12 text-center text-sm text-muted">No captured evidence yet. Detected frames will appear here automatically.</div>}</div>}</section>
  </main>;
}
