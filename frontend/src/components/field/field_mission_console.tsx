"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Activity, Camera, CheckCircle2, FileText, Gauge, MapPin, Navigation, Radar, RotateCcw, Send, ShieldCheck, Siren, Wifi, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/page";

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";
const RESULT_KEY = "sentry.field.result";

const LABELS: Record<string, string> = {
  pothole: "Pothole", road_crack: "Road crack", streetlight: "Streetlight", cctv_camera: "CCTV",
  signboard: "Signboard", drain: "Drain / manhole", solar_panel: "Solar panel", road_barrier: "Road barrier",
  manhole_cover: "Manhole cover", asset_qr: "QR / asset ID", asset_text: "OCR / asset text", asset_barcode: "Barcode",
};

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type Tender = {
  id: string; reference_number: string; title: string; procuring_entity?: string | null; source_url?: string | null;
  contract_location?: string | null; category?: string | null; machine?: string | null; demo_site?: string | null;
  requirements: Requirement[]; verification_notes?: string | null; auto_generated?: boolean;
};
type Gps = { status?: string; source?: string | null; lat?: number | null; lon?: number | null; accuracy_m?: number | null; captured_at?: number | null };
type EventItem = { type: string; capability?: string; observation?: string; confidence?: number; track_id?: string | null; detector?: string; mission_id?: string | null; requirement_id?: string | null; tender_id?: string | null; observed_at?: number; frame_url?: string | null; gps?: Gps };
type Status = {
  running: boolean; authorized: boolean; camera_url: string; fps: number; inference_ms: number; findings: number; evidence: number;
  last_detection: { type: string; confidence: number; track_id?: string | null } | null; last_error: string | null;
  mission_id: string | null; requirement_id: string | null; tender_id: string | null; capabilities: string[]; machine: string | null;
  demo_site: string | null; machine_id: string | null; gps: Gps; recent_events: EventItem[];
};
type Reanalysis = {
  status: string; mission_id: string; summary: { expected_total: number; observed_total: number; gap_total: number; evidence_count: number; gps_evidence_count: number; observation_count: number };
  discrepancies: { requirement_id: string; capability: string; label: string; expected: number; observed: number; gap: number; signal: string }[];
  possible_explanations: string[]; next_checks: string[]; guardrail: string;
};

const EMPTY: Status = {
  running: false, authorized: false, camera_url: DEFAULT_CAMERA, fps: 0, inference_ms: 0, findings: 0, evidence: 0,
  last_detection: null, last_error: null, mission_id: null, requirement_id: null, tender_id: null, capabilities: [],
  machine: null, demo_site: null, machine_id: null, gps: { status: "unavailable" }, recent_events: [],
};

export function FieldMissionConsole({ tenderKey, requirementId }: { tenderKey?: string; requirementId?: string }) {
  const router = useRouter();
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
  const [busy, setBusy] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);

  const capabilities = useMemo(() => Array.from(new Set((tender?.requirements || []).map((item) => item.capability).filter(Boolean))), [tender]);
  const evidenceEvents = useMemo(() => events.filter((event) => event.type === "evidence" && event.frame_url), [events]);
  const gpsLive = status.gps?.status === "live" && status.gps.lat != null && status.gps.lon != null;
  const missionLive = Boolean(streamUrl && status.running);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        if (!tenderKey) throw new Error("No tender was supplied to SENTRY FIELD");
        const response = await fetch(`${BACKEND}/api/investigations/tenders/${encodeURIComponent(tenderKey)}/field-verification`, { cache: "no-store" });
        if (!response.ok) throw new Error(`FIELD plan unavailable (${response.status})`);
        const resolved = await response.json() as Tender;
        if (!resolved.requirements?.length) throw new Error("FIELD plan has no executable requirements");
        const primary = resolved.requirements.find((item) => item.id === requirementId) ?? resolved.requirements[0];
        if (alive) {
          setTender(resolved);
          setPrimaryRequirement(primary);
          setCamera(localStorage.getItem("sentry.camera.url") || DEFAULT_CAMERA);
          setError(null);
        }
      } catch (reason) {
        if (alive) setError(reason instanceof Error ? reason.message : "FIELD plan could not be resolved");
      }
    };
    void load();
    return () => { alive = false; };
  }, [requirementId, tenderKey]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [healthResponse, statusResponse, eventsResponse] = await Promise.all([
          fetch(`${API}/health`, { cache: "no-store" }),
          fetch(`${API}/status`, { cache: "no-store" }),
          fetch(`${API}/events`, { cache: "no-store" }),
        ]);
        if (!statusResponse.ok || !eventsResponse.ok) throw new Error();
        const nextStatus = await statusResponse.json() as Status;
        const nextEvents = await eventsResponse.json() as { events?: EventItem[] };
        if (alive) {
          setOnline(healthResponse.ok);
          setStatus(nextStatus);
          setEvents(Array.isArray(nextEvents.events) ? nextEvents.events : []);
        }
      } catch {
        if (alive) setOnline(false);
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 700);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => () => {
    if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current);
  }, []);

  function stopGps() {
    if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setGpsWatching(false);
  }

  function startGps(missionId: string) {
    if (!("geolocation" in navigator) || !tender || !primaryRequirement) return;
    stopGps();
    const machineId = `browser-gps:${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    watchId.current = navigator.geolocation.watchPosition(async (position) => {
      await fetch(`${API}/telemetry/mobile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_id: tender.id, mission_id: missionId, requirement_id: primaryRequirement.id, machine_id: machineId,
          lat: position.coords.latitude, lon: position.coords.longitude, accuracy_m: position.coords.accuracy,
          captured_at: position.timestamp, speed: position.coords.speed,
        }),
      }).catch(() => undefined);
    }, () => setGpsWatching(false), { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 });
    setGpsWatching(true);
  }

  async function startMission() {
    if (!tender || !primaryRequirement || !capabilities.length) return setError("SENTRY could not derive a physical inspection plan.");
    const source = camera.trim();
    if (!source) return setError("Camera URL is required.");
    setBusy(true); setError(null); setCameraError(null);
    localStorage.setItem("sentry.camera.url", source);
    try {
      const missionId = `${tender.id}-${Date.now()}`;
      const dispatch = await fetch(`${API}/dispatch`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_id: tender.id, mission_id: missionId, requirement_id: primaryRequirement.id,
          capability: primaryRequirement.capability, capabilities, machine: tender.machine || "Normal Vision Rover", demo_site: tender.demo_site || null,
        }),
      });
      const payload = await dispatch.json().catch(() => ({}));
      if (!dispatch.ok) throw new Error(payload.detail || "FIELD mission authorisation failed");
      startGps(missionId);
      const query = new URLSearchParams({
        camera_url: source, confidence: String(confidence), every_n_frames: String(everyNFrames), mission_id: missionId,
        requirement_id: primaryRequirement.id, capabilities: capabilities.join(","), t: String(Date.now()),
      });
      setStreamUrl(`${API}/stream?${query.toString()}`);
      setStatus((current) => ({ ...current, running: true, authorized: true, mission_id: missionId, requirement_id: primaryRequirement.id, tender_id: tender.id, capabilities }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "FIELD mission could not start");
      stopGps();
    } finally {
      setBusy(false);
    }
  }

  async function stopMission() {
    await fetch(`${API}/stop`, { method: "POST" }).catch(() => undefined);
    setStreamUrl(null); stopGps();
    setStatus((current) => ({ ...current, running: false, authorized: false }));
  }

  async function completeAndSend() {
    if (!tender || !status.mission_id) return;
    const observations = events
      .filter((event) => event.type === "evidence" || event.type === "detection")
      .map((event) => ({ capability: event.capability || event.type, observation: event.observation || "Field observation", confidence: event.confidence, track_id: event.track_id, frame_url: event.frame_url, gps: event.gps, observed_at: event.observed_at }));
    if (!observations.length) return setError("Capture at least one field observation before returning to SENTRY.");
    setBusy(true); setError(null);
    try {
      const response = await fetch(`${BACKEND}/api/investigations/field-reanalysis`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tender_id: tender.id, mission_id: status.mission_id, requirements: tender.requirements, observations }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "SENTRY re-analysis failed");
      sessionStorage.setItem(RESULT_KEY, JSON.stringify(payload));
      await stopMission();
      router.push(`/investigate?q=${encodeURIComponent(`TENDER:${tender.reference_number}`)}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not return FIELD results to SENTRY");
    } finally {
      setBusy(false);
    }
  }

  if (!tender || !primaryRequirement) {
    return <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm"><div className="flex items-center gap-2 text-sm text-muted">{error ? <XCircle className="h-4 w-4 text-danger" /> : <Activity className="h-4 w-4 animate-pulse text-accent" />}{error || "Resolving exact tender → FIELD mission…"}</div></section>;
  }

  return (
    <main className="mx-auto w-full max-w-[1900px] space-y-5">
      <section className="rounded-2xl border border-accent/20 bg-surface p-5 shadow-sm md:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / AUTONOMOUS MISSION</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">Physical verification</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">SENTRY selects the capabilities. FIELD captures live visual observations and mobile GPS, then sends the evidence back to SENTRY for re-analysis.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={online ? "success" : "muted"}><Wifi className="mr-1 inline h-3 w-3" />{online ? "Gateway online" : "Gateway offline"}</Badge>
            <Badge tone={gpsLive ? "success" : gpsWatching ? "muted" : "muted"}><Navigation className="mr-1 inline h-3 w-3" />{gpsLive ? "GPS live" : gpsWatching ? "GPS waiting" : "GPS idle"}</Badge>
            {missionLive ? <button type="button" onClick={() => void stopMission()} className="inline-flex items-center gap-2 rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-xs font-semibold text-danger"><Siren className="h-3.5 w-3.5" />Stop mission</button> : <button type="button" onClick={() => void startMission()} disabled={!online || busy} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:opacity-40"><ShieldCheck className="h-3.5 w-3.5" />{busy ? "Starting…" : "Start SENTRY FIELD"}</button>}
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[1.8fr_1fr_1fr]">
          <Info label="Exact tender" value={tender.title} detail={`${tender.reference_number}${tender.contract_location ? ` · ${tender.contract_location}` : ""}`} />
          <Info label="Primary requirement" value={primaryRequirement.label} detail={`${primaryRequirement.id} · expected ${primaryRequirement.expected_quantity}`} />
          <Info label="Machine" value={tender.machine || "Normal Vision Rover"} detail={tender.demo_site || "Operator-selected site"} />
        </div>

        <div className="mt-4 rounded-xl border border-accent/20 bg-accent/5 p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.15em] text-accent"><Radar className="h-3.5 w-3.5" /> Auto-selected capabilities</div>
          <div className="mt-3 flex flex-wrap gap-2">{capabilities.map((capability) => <span key={capability} className="rounded-full border border-accent/25 bg-accent/10 px-3 py-1.5 text-[11px] font-semibold text-text">{LABELS[capability] || capability}</span>)}</div>
          <div className="mt-2 text-[11px] text-muted">No manual detector selection.</div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_150px_150px]">
          <label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Camera source</span><input value={camera} onChange={(event) => setCamera(event.target.value)} disabled={missionLive} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50 disabled:opacity-70" placeholder="DroidCam /video URL" /></label>
          <label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Confidence</span><input type="number" min="0.05" max="0.99" step="0.01" value={confidence} onChange={(event) => setConfidence(Number(event.target.value))} disabled={missionLive} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none disabled:opacity-70" /></label>
          <label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Frame cadence</span><input type="number" min="1" max="60" value={everyNFrames} onChange={(event) => setEveryNFrames(Math.max(1, Number(event.target.value)))} disabled={missionLive} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none disabled:opacity-70" /></label>
        </div>
        {error ? <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2.5 text-xs text-danger">{error}</div> : null}
        {cameraError ? <div className="mt-3 rounded-xl border border-warning/30 bg-warning/10 px-3 py-2.5 text-xs text-warning">{cameraError}</div> : null}
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
        <Metric label="State" value={missionLive ? "LIVE" : status.authorized ? "READY" : "IDLE"} />
        <Metric label="FPS" value={status.fps.toFixed(1)} icon={<Gauge className="h-4 w-4" />} />
        <Metric label="Inference" value={`${status.inference_ms.toFixed(0)} ms`} icon={<Gauge className="h-4 w-4" />} />
        <Metric label="Findings" value={String(status.findings)} icon={<Radar className="h-4 w-4" />} />
        <Metric label="Evidence" value={String(status.evidence)} icon={<FileText className="h-4 w-4" />} />
        <Metric label="GPS" value={gpsLive ? `${status.gps.lat!.toFixed(5)}, ${status.gps.lon!.toFixed(5)}` : "Waiting"} icon={<MapPin className="h-4 w-4" />} />
      </section>

      <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        <div className="flex flex-col gap-3 border-b border-border px-4 py-3 md:flex-row md:items-center md:justify-between"><div className="flex gap-1 rounded-lg bg-surface-2 p-1"><button type="button" onClick={() => setTab("live")} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${tab === "live" ? "bg-surface text-text" : "text-muted"}`}>Live camera</button><button type="button" onClick={() => setTab("evidence")} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${tab === "evidence" ? "bg-surface text-text" : "text-muted"}`}>Evidence ({evidenceEvents.length})</button></div><div className="text-[10px] uppercase tracking-[.14em] text-faint">Mission {status.mission_id || "—"}</div></div>
        {tab === "live" ? <div className="p-3"><div className="relative min-h-[55vh] overflow-hidden rounded-xl bg-[#0b0e13]">{streamUrl ? <img key={streamUrl} src={streamUrl} alt="SENTRY FIELD live annotated camera" className="h-full min-h-[55vh] w-full object-contain" onLoad={() => setCameraError(null)} onError={() => setCameraError("Live stream failed. Check the DroidCam /video URL and FIELD gateway terminal.")} /> : <div className="absolute inset-0 grid place-items-center text-center"><div><Camera className="mx-auto h-10 w-10 text-accent" /><div className="mt-3 text-sm font-semibold text-text">SENTRY FIELD ready</div><div className="mt-1 max-w-md text-xs leading-5 text-muted">Start the mission to open the camera and inference pipeline.</div></div></div>}<div className="absolute left-4 top-4 flex flex-wrap gap-2"><Badge tone={missionLive ? "success" : "muted"}>{missionLive ? "LIVE" : "IDLE"}</Badge>{status.last_detection ? <Badge tone="success">{LABELS[status.last_detection.type] || status.last_detection.type} · {Math.round(status.last_detection.confidence * 100)}%</Badge> : null}</div></div></div> : <div className="divide-y divide-border">{evidenceEvents.length ? evidenceEvents.slice(0, 100).map((event, index) => <EvidenceCard key={`${event.observed_at || 0}-${event.track_id || index}`} event={event} />) : <div className="p-12 text-center text-sm text-muted">No captured evidence yet.</div>}</div>}
      </section>

      <div className="flex justify-end"><button type="button" onClick={() => void completeAndSend()} disabled={!status.mission_id || busy || !events.some((event) => event.type === "evidence" || event.type === "detection")} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:opacity-40"><Send className="h-3.5 w-3.5" />{busy ? "Returning to SENTRY…" : "Complete verification → SENTRY"}</button></div>
    </main>
  );
}

function Info({ label, value, detail }: { label: string; value: string; detail?: string | null }) { return <div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">{label}</div><div className="mt-1 text-sm font-semibold text-text">{value}</div>{detail ? <div className="mt-1 text-xs text-muted">{detail}</div> : null}</div>; }
function Metric({ label, value, icon }: { label: string; value: string; icon?: ReactNode }) { return <div className="rounded-2xl border border-border bg-surface p-4"><div className="flex items-center justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>{label}</span>{icon}</div><div className="mt-2 text-xl font-semibold text-text">{value}</div></div>; }
function EvidenceCard({ event }: { event: EventItem }) {
  const url = event.frame_url ? (event.frame_url.startsWith("http") ? event.frame_url : `${API}${event.frame_url}`) : null;
  return <div className="grid gap-4 p-4 md:grid-cols-[200px_1fr_auto] md:items-center"><div className="aspect-video overflow-hidden rounded-xl border border-border bg-surface-2">{url ? <a href={url} target="_blank" rel="noreferrer"><img src={url} alt="Captured SENTRY FIELD evidence" className="h-full w-full object-cover" /></a> : null}</div><div><div className="text-sm font-semibold text-text">{LABELS[event.capability || ""] || event.capability || event.type}</div><div className="mt-1 text-xs text-muted">{event.observation || "Field observation"}</div>{event.confidence != null ? <div className="mt-1 text-xs text-faint">Confidence {Math.round(event.confidence * 100)}%</div> : null}{event.gps?.lat != null && event.gps?.lon != null ? <div className="mt-1 text-xs text-faint">GPS {event.gps.lat.toFixed(6)}, {event.gps.lon.toFixed(6)}</div> : null}</div><Badge tone="success"><CheckCircle2 className="mr-1 inline h-3 w-3" />Captured</Badge></div>;
}
