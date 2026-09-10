"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Camera, CheckCircle2, History, MapPin, Navigation, Radar, RotateCcw, ShieldCheck, Siren, Wifi, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/page";

const FIELD_API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";

const LABELS: Record<string, string> = {
  pothole: "Pothole", road_crack: "Road crack", streetlight: "Streetlight", cctv_camera: "CCTV",
  signboard: "Signboard", drain: "Drain / manhole", solar_panel: "Solar panel", road_barrier: "Road barrier",
  manhole_cover: "Manhole cover", asset_qr: "QR / asset ID", asset_text: "OCR / asset text", asset_barcode: "Barcode",
};

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type Tender = {
  id: string; reference_number: string; title: string; procuring_entity?: string | null; category?: string | null;
  machine?: string | null; demo_site?: string | null; contract_location?: string | null; requirements: Requirement[];
};
type Gps = { status?: string; source?: string | null; lat?: number | null; lon?: number | null; accuracy_m?: number | null };
type EventItem = { type: string; capability?: string; observation?: string; confidence?: number; track_id?: string | null; frame_url?: string | null; gps?: Gps; observed_at?: number };
type FieldStatus = {
  running: boolean; authorized: boolean; fps: number; inference_ms: number; findings: number; evidence: number;
  mission_id: string | null; requirement_id: string | null; tender_id: string | null; capabilities: string[]; gps: Gps;
};
type Verification = { id: string; version: number; status: string; mission_id: string; submitted_at?: string | null; updated_at?: string | null; observation_count: number; evidence_count: number; gps_evidence_count: number };
type VerificationStatus = { verified: boolean; latest: Verification | null; history: Verification[]; deletion_allowed: boolean; update_allowed: boolean };

const EMPTY: FieldStatus = { running: false, authorized: false, fps: 0, inference_ms: 0, findings: 0, evidence: 0, mission_id: null, requirement_id: null, tender_id: null, capabilities: [], gps: { status: "unavailable" } };

export function FieldMissionConsoleV2({ tenderKey, requirementId }: { tenderKey?: string; requirementId?: string }) {
  const router = useRouter();
  const [tender, setTender] = useState<Tender | null>(null);
  const [primaryRequirement, setPrimaryRequirement] = useState<Requirement | null>(null);
  const [status, setStatus] = useState<FieldStatus>(EMPTY);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [verification, setVerification] = useState<VerificationStatus | null>(null);
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [confidence, setConfidence] = useState(0.55);
  const [everyNFrames, setEveryNFrames] = useState(1);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const [gpsWatching, setGpsWatching] = useState(false);
  const [tab, setTab] = useState<"live" | "evidence">("live");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);

  const capabilities = useMemo(() => Array.from(new Set((tender?.requirements || []).map((item) => item.capability).filter(Boolean))), [tender]);
  const evidenceEvents = useMemo(() => events.filter((event) => event.type === "evidence" && event.frame_url), [events]);
  const missionLive = Boolean(streamUrl && status.running);
  const gpsLive = status.gps?.status === "live" && status.gps.lat != null && status.gps.lon != null;
  const completed = Boolean(verification?.verified);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        if (!tenderKey) throw new Error("No tender was supplied to SENTRY FIELD");
        const response = await fetch(`${BACKEND}/api/investigations/tenders/${encodeURIComponent(tenderKey)}/field-verification`, { cache: "no-store" });
        if (!response.ok) throw new Error(`FIELD plan unavailable (${response.status})`);
        const resolved = await response.json() as Tender;
        if (!resolved.requirements?.length) throw new Error("FIELD plan has no executable requirements");
        const primary = resolved.requirements.find((item) => item.id === requirementId) ?? resolved.requirements[0];
        const statusResponse = await fetch(`${BACKEND}/api/investigations/tenders/${encodeURIComponent(resolved.id)}/field-verification-status`, { cache: "no-store" });
        const saved = statusResponse.ok ? await statusResponse.json() as VerificationStatus : null;
        if (alive) {
          setTender(resolved);
          setPrimaryRequirement(primary);
          setVerification(saved);
          setCamera(localStorage.getItem("sentry.camera.url") || DEFAULT_CAMERA);
          setError(null);
        }
      } catch (reason) {
        if (alive) setError(reason instanceof Error ? reason.message : "FIELD plan could not be resolved");
      }
    }
    void load();
    return () => { alive = false; };
  }, [requirementId, tenderKey]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [healthResponse, statusResponse, eventsResponse] = await Promise.all([
          fetch(`${FIELD_API}/health`, { cache: "no-store" }),
          fetch(`${FIELD_API}/status`, { cache: "no-store" }),
          fetch(`${FIELD_API}/events`, { cache: "no-store" }),
        ]);
        if (!statusResponse.ok || !eventsResponse.ok) throw new Error();
        const nextStatus = await statusResponse.json() as FieldStatus;
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
      await fetch(`${FIELD_API}/telemetry/mobile`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tender_id: tender.id, mission_id: missionId, requirement_id: primaryRequirement.id, machine_id: machineId, lat: position.coords.latitude, lon: position.coords.longitude, accuracy_m: position.coords.accuracy, captured_at: position.timestamp, speed: position.coords.speed }),
      }).catch(() => undefined);
    }, () => setGpsWatching(false), { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 });
    setGpsWatching(true);
  }

  async function startMission() {
    if (!tender || !primaryRequirement || !capabilities.length) return setError("SENTRY could not derive a physical inspection plan.");
    const source = camera.trim();
    if (!source) return setError("Camera URL is required.");
    setBusy(true); setError(null); localStorage.setItem("sentry.camera.url", source);
    try {
      const missionId = `${tender.id}-${Date.now()}`;
      const dispatch = await fetch(`${FIELD_API}/dispatch`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tender_id: tender.id, mission_id: missionId, requirement_id: primaryRequirement.id, capability: primaryRequirement.capability, capabilities, machine: tender.machine || "Normal Vision Rover", demo_site: tender.demo_site || null }),
      });
      const payload = await dispatch.json().catch(() => ({}));
      if (!dispatch.ok) throw new Error(payload.detail || "FIELD mission authorisation failed");
      startGps(missionId);
      const query = new URLSearchParams({ camera_url: source, confidence: String(confidence), every_n_frames: String(everyNFrames), mission_id: missionId, requirement_id: primaryRequirement.id, capabilities: capabilities.join(","), t: String(Date.now()) });
      setStreamUrl(`${FIELD_API}/stream?${query.toString()}`);
      setStatus((current) => ({ ...current, running: true, authorized: true, mission_id: missionId, requirement_id: primaryRequirement.id, tender_id: tender.id, capabilities }));
      setTab("live");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "FIELD mission could not start");
      stopGps();
    } finally { setBusy(false); }
  }

  async function stopMission() {
    await fetch(`${FIELD_API}/stop`, { method: "POST" }).catch(() => undefined);
    setStreamUrl(null); stopGps();
    setStatus((current) => ({ ...current, running: false, authorized: false }));
  }

  async function submitVerification() {
    if (!tender || !status.mission_id) return setError("Start a FIELD mission before submitting verification.");
    const observations = events.filter((event) => event.type === "evidence" || event.type === "detection").map((event) => ({ capability: event.capability || event.type, observation: event.observation || "Field observation", confidence: event.confidence, track_id: event.track_id, frame_url: event.frame_url, gps: event.gps, observed_at: event.observed_at }));
    if (!observations.length) return setError("Capture at least one field observation before submitting verification.");
    setBusy(true); setError(null);
    try {
      const response = await fetch(`${BACKEND}/api/investigations/field-reanalysis`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tender_id: tender.id, mission_id: status.mission_id, requirements: tender.requirements, observations }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "SENTRY verification save failed");
      const verificationPayload = payload.verification as Verification;
      setVerification((current) => ({ verified: true, latest: verificationPayload, history: [...(current?.history || []), verificationPayload], deletion_allowed: false, update_allowed: true }));
      await stopMission();
      setTab("evidence");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save field verification");
    } finally { setBusy(false); }
  }

  if (!tender || !primaryRequirement) {
    return <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm"><div className="flex items-center gap-2 text-sm text-muted">{error ? <XCircle className="h-4 w-4 text-danger" /> : <Activity className="h-4 w-4 animate-pulse text-accent" />}{error || "Resolving exact tender → FIELD mission…"}</div></section>;
  }

  return (
    <main className="mx-auto w-full max-w-[1900px] space-y-5">
      <section className="rounded-2xl border border-accent/20 bg-surface p-5 shadow-sm md:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / VERIFICATION RECORD</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">{completed ? "Update physical verification" : "Physical verification"}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">Original submissions are preserved. {completed ? `You are creating verification version ${(verification?.latest?.version || 1) + 1}; the previous record remains immutable.` : "The first completed submission becomes the immutable verification version 1."}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={completed ? "success" : "muted"}>{completed ? `Verified v${verification?.latest?.version}` : "Not yet verified"}</Badge>
            <Badge tone={online ? "success" : "muted"}><Wifi className="mr-1 inline h-3 w-3" />{online ? "Gateway online" : "Gateway offline"}</Badge>
            <Badge tone={gpsLive ? "success" : "muted"}><Navigation className="mr-1 inline h-3 w-3" />{gpsLive ? "GPS live" : gpsWatching ? "GPS waiting" : "GPS idle"}</Badge>
            {missionLive ? <button type="button" onClick={() => void stopMission()} className="inline-flex items-center gap-2 rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-xs font-semibold text-danger"><Siren className="h-3.5 w-3.5" />Stop mission</button> : <button type="button" onClick={() => void startMission()} disabled={!online || busy} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:opacity-40"><ShieldCheck className="h-3.5 w-3.5" />{busy ? "Starting…" : completed ? "Start update mission" : "Start SENTRY FIELD"}</button>}
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
          <div className="mt-2 text-[10px] text-muted">Capabilities are derived from the tender; verification updates create a new version instead of overwriting the prior submission.</div>
        </div>

        {completed ? (
          <div className="mt-4 flex items-center gap-3 rounded-xl border border-success/20 bg-success/5 p-4 text-xs text-text">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
            <div><span className="font-semibold">Verification history preserved.</span> Delete is disabled at the application level; updates are append-only versions.</div>
          </div>
        ) : null}

        {error ? <div className="mt-4 rounded-xl border border-danger/25 bg-danger/5 p-3 text-xs text-danger">{error}</div> : null}
      </section>

      <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm md:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setTab("live")} className={`rounded-lg px-3 py-2 text-xs font-semibold ${tab === "live" ? "bg-accent/10 text-accent" : "text-muted"}`}><Camera className="mr-1 inline h-3.5 w-3.5" />Live</button>
            <button type="button" onClick={() => setTab("evidence")} className={`rounded-lg px-3 py-2 text-xs font-semibold ${tab === "evidence" ? "bg-accent/10 text-accent" : "text-muted"}`}><History className="mr-1 inline h-3.5 w-3.5" />Evidence & history</button>
          </div>
          <span className="text-xs text-muted">{status.findings} findings · {evidenceEvents.length} evidence frames</span>
        </div>

        {tab === "live" ? (
          <div className="mt-4 space-y-4">
            <div className="aspect-video overflow-hidden rounded-2xl border border-border bg-[#0b0e13]">
              {streamUrl ? <img src={streamUrl} alt="SENTRY FIELD live annotated camera" className="h-full w-full object-contain" /> : <div className="grid h-full place-items-center p-8 text-center text-muted"><div><Camera className="mx-auto h-8 w-8" /><div className="mt-3 text-sm font-semibold text-text">{completed ? "Start an update mission" : "Start SENTRY FIELD"}</div><div className="mt-1 text-xs">Connect DroidCam / camera, start the mission, then capture evidence.</div></div></div>}
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Metric label="FPS" value={status.fps.toFixed(1)} />
              <Metric label="Inference" value={`${status.inference_ms.toFixed(0)} ms`} />
              <Metric label="Evidence" value={String(evidenceEvents.length)} />
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-border p-4 md:flex-row md:items-end">
              <label className="flex-1 text-xs text-muted">Camera URL<input value={camera} onChange={(event) => setCamera(event.target.value)} className="mt-1.5 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-text" /></label>
              <label className="w-full md:w-40 text-xs text-muted">Confidence<input type="number" min="0.1" max="0.99" step="0.05" value={confidence} onChange={(event) => setConfidence(Number(event.target.value) || 0.55)} className="mt-1.5 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-text" /></label>
              <label className="w-full md:w-40 text-xs text-muted">Every N frames<input type="number" min="1" max="12" step="1" value={everyNFrames} onChange={(event) => setEveryNFrames(Math.max(1, Number(event.target.value) || 1))} className="mt-1.5 w-full rounded-lg border border-border bg-bg px-3 py-2 text-xs text-text" /></label>
            </div>
          </div>
        ) : (
          <div className="mt-4 grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <div>
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.15em] text-accent"><History className="h-3.5 w-3.5" /> Verification history</div>
              <div className="mt-3 space-y-2">
                {(verification?.history || []).slice().reverse().map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-xl border border-border p-3 text-xs">
                    <div><span className="font-semibold text-text">Version {item.version}</span><span className="ml-2 text-muted">{item.status}</span><div className="mt-1 text-[10px] text-faint">{item.submitted_at ? new Date(item.submitted_at).toLocaleString() : ""} · {item.evidence_count} evidence · {item.gps_evidence_count} GPS</div></div>
                    <Badge tone="success">immutable</Badge>
                  </div>
                ))}
                {!verification?.history?.length ? <div className="rounded-xl border border-border p-4 text-xs text-muted">No submitted verification yet.</div> : null}
              </div>
            </div>
            <div className="rounded-xl border border-accent/20 bg-accent/5 p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[.15em] text-accent">Submit rule</div>
              <div className="mt-2 text-sm font-semibold text-text">{completed ? `Create version ${(verification?.latest?.version || 1) + 1}` : "Create version 1"}</div>
              <div className="mt-2 text-xs leading-5 text-muted">The current evidence becomes the new verification version. Earlier versions remain available for audit and cannot be deleted through SENTRY.</div>
              <button type="button" disabled={!missionLive || busy} onClick={() => void submitVerification()} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:opacity-40"><RotateCcw className="h-3.5 w-3.5" />{busy ? "Saving…" : completed ? "Update Verification" : "Complete Verification"}</button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

function Info({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="rounded-xl border border-border bg-bg/20 p-4"><div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{label}</div><div className="mt-2 text-sm font-semibold text-text">{value}</div><div className="mt-1 text-xs text-muted">{detail}</div></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-border p-3"><div className="text-[10px] uppercase tracking-[.14em] text-faint">{label}</div><div className="mt-1 text-sm font-semibold text-text">{value}</div></div>;
}
