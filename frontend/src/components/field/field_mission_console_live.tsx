"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Camera, CheckCircle2, History, Navigation, Radar, ShieldCheck, Siren, Wifi, XCircle } from "lucide-react";
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
type Tender = { id: string; reference_number: string; title: string; procuring_entity?: string | null; category?: string | null; machine?: string | null; demo_site?: string | null; contract_location?: string | null; requirements: Requirement[] };
type Gps = { status?: string; source?: string | null; lat?: number | null; lon?: number | null; accuracy_m?: number | null };
type EventItem = { type: string; capability?: string; observation?: string; confidence?: number; track_id?: string | null; frame_url?: string | null; gps?: Gps; observed_at?: number };
type FieldStatus = { running: boolean; authorized: boolean; fps: number; inference_ms: number; findings: number; evidence: number; mission_id: string | null; requirement_id: string | null; tender_id: string | null; capabilities: string[]; gps: Gps };
type Verification = { id: string; version: number; status: string; mission_id: string; submitted_at?: string | null; observation_count: number; evidence_count: number; gps_evidence_count: number };
type VerificationStatus = { verified: boolean; latest: Verification | null; history: Verification[]; deletion_allowed: boolean; update_allowed: boolean };
const EMPTY: FieldStatus = { running: false, authorized: false, fps: 0, inference_ms: 0, findings: 0, evidence: 0, mission_id: null, requirement_id: null, tender_id: null, capabilities: [], gps: { status: "unavailable" } };

function evidenceUrl(path: string) { return path.startsWith("http") ? path : `${FIELD_API}${path}`; }

export function FieldMissionConsoleLive({ tenderKey, requirementId }: { tenderKey?: string; requirementId?: string }) {
  const [tender, setTender] = useState<Tender | null>(null);
  const [req, setReq] = useState<Requirement | null>(null);
  const [status, setStatus] = useState<FieldStatus>(EMPTY);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [verification, setVerification] = useState<VerificationStatus | null>(null);
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [everyNFrames, setEveryNFrames] = useState(1);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const [gpsWatching, setGpsWatching] = useState(false);
  const [tab, setTab] = useState<"live" | "evidence">("live");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);
  const capabilities = useMemo(() => Array.from(new Set((tender?.requirements || []).map((x) => x.capability).filter(Boolean))), [tender]);
  const evidenceEvents = useMemo(() => events.filter((e) => e.type === "evidence" && e.frame_url), [events]);
  const detectionEvents = useMemo(() => events.filter((e) => e.type === "detection"), [events]);
  const completed = Boolean(verification?.verified);
  const gpsLive = status.gps?.status === "live" && status.gps.lat != null && status.gps.lon != null;
  const live = Boolean(streamUrl && status.running);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        if (!tenderKey) throw new Error("No tender was supplied to SENTRY FIELD");
        const planResponse = await fetch(`${BACKEND}/api/investigations/tenders/${encodeURIComponent(tenderKey)}/field-verification`, { cache: "no-store" });
        if (!planResponse.ok) throw new Error(`FIELD plan unavailable (${planResponse.status})`);
        const plan = await planResponse.json() as Tender;
        const primary = plan.requirements?.find((x) => x.id === requirementId) ?? plan.requirements?.[0];
        if (!primary) throw new Error("FIELD plan has no executable requirements");
        const statusResponse = await fetch(`${BACKEND}/api/investigations/tenders/${encodeURIComponent(plan.id)}/field-verification-status`, { cache: "no-store" });
        const saved = statusResponse.ok ? await statusResponse.json() as VerificationStatus : null;
        if (alive) { setTender(plan); setReq(primary); setVerification(saved); setCamera(localStorage.getItem("sentry.camera.url") || DEFAULT_CAMERA); }
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : "FIELD plan could not be resolved"); }
    })();
    return () => { alive = false; };
  }, [requirementId, tenderKey]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [h, s, e] = await Promise.all([fetch(`${FIELD_API}/health`, { cache: "no-store" }), fetch(`${FIELD_API}/status`, { cache: "no-store" }), fetch(`${FIELD_API}/events`, { cache: "no-store" })]);
        if (!s.ok || !e.ok) throw new Error();
        const nextStatus = await s.json() as FieldStatus;
        const nextEvents = await e.json() as { events?: EventItem[] };
        if (alive) { setOnline(h.ok); setStatus(nextStatus); setEvents(Array.isArray(nextEvents.events) ? nextEvents.events : []); }
      } catch { if (alive) setOnline(false); }
    };
    void poll(); const id = window.setInterval(() => void poll(), 350);
    return () => { alive = false; window.clearInterval(id); };
  }, []);

  useEffect(() => () => { if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current); }, []);

  function stopGps() { if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current); watchId.current = null; setGpsWatching(false); }
  function startGps(missionId: string) {
    if (!("geolocation" in navigator) || !tender || !req) return;
    stopGps();
    const machineId = `browser-gps:${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    watchId.current = navigator.geolocation.watchPosition(async (p) => {
      await fetch(`${FIELD_API}/telemetry/mobile`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tender_id: tender.id, mission_id: missionId, requirement_id: req.id, machine_id: machineId, lat: p.coords.latitude, lon: p.coords.longitude, accuracy_m: p.coords.accuracy, captured_at: p.timestamp, speed: p.coords.speed }) }).catch(() => undefined);
    }, () => setGpsWatching(false), { enableHighAccuracy: true, maximumAge: 1000, timeout: 8000 });
    setGpsWatching(true);
  }

  async function startMission() {
    if (!tender || !req || !capabilities.length) return setError("SENTRY could not derive a physical inspection plan.");
    const source = camera.trim(); if (!source) return setError("Camera URL is required.");
    setBusy(true); setError(null); localStorage.setItem("sentry.camera.url", source);
    try {
      const missionId = `${tender.id}-${Date.now()}`;
      const dispatch = await fetch(`${FIELD_API}/dispatch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tender_id: tender.id, mission_id: missionId, requirement_id: req.id, capability: req.capability, capabilities, machine: tender.machine || "Normal Vision Rover", demo_site: tender.demo_site || null }) });
      const p = await dispatch.json().catch(() => ({})); if (!dispatch.ok) throw new Error(p.detail || "FIELD mission authorisation failed");
      startGps(missionId);
      const query = new URLSearchParams({ camera_url: source, confidence: "0.55", every_n_frames: String(everyNFrames), mission_id: missionId, requirement_id: req.id, capabilities: capabilities.join(",") });
      setStreamUrl(`${FIELD_API}/stream?${query}&t=${Date.now()}`); setStatus((s) => ({ ...s, running: true, authorized: true, mission_id: missionId, requirement_id: req.id, tender_id: tender.id, capabilities })); setTab("live");
    } catch (e) { setError(e instanceof Error ? e.message : "FIELD mission could not start"); stopGps(); } finally { setBusy(false); }
  }

  async function stopMission() { await fetch(`${FIELD_API}/stop`, { method: "POST" }).catch(() => undefined); setStreamUrl(null); stopGps(); setStatus((s) => ({ ...s, running: false, authorized: false })); }

  async function submitVerification() {
    if (!tender || !status.mission_id) return setError("Start a FIELD mission before submitting verification.");
    const observations = events.filter((e) => e.type === "evidence").map((e) => ({ capability: e.capability || "evidence", observation: e.observation || "Field observation", confidence: e.confidence, track_id: e.track_id, frame_url: e.frame_url, gps: e.gps, observed_at: e.observed_at }));
    if (!observations.length) return setError("Capture at least one detected evidence frame before submitting verification.");
    setBusy(true); setError(null);
    try {
      const r = await fetch(`${BACKEND}/api/investigations/field-reanalysis`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tender_id: tender.id, mission_id: status.mission_id, requirements: tender.requirements, observations }) });
      const p = await r.json().catch(() => ({})); if (!r.ok) throw new Error(p.detail || "SENTRY verification save failed");
      const saved = p.verification as Verification;
      setVerification((current) => ({ verified: true, latest: saved, history: [...(current?.history || []), saved], deletion_allowed: false, update_allowed: true }));
      await stopMission(); setTab("evidence");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save field verification"); } finally { setBusy(false); }
  }

  if (!tender || !req) return <section className="rounded-2xl border border-border bg-surface p-6"><div className="flex items-center gap-2 text-sm text-muted">{error ? <XCircle className="h-4 w-4 text-danger" /> : <Activity className="h-4 w-4 animate-pulse text-accent" />}{error || "Resolving exact tender → FIELD mission…"}</div></section>;

  return <main className="mx-auto w-full max-w-[1900px] space-y-5">
    <section className="rounded-2xl border border-accent/20 bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between"><div><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / VERIFICATION RECORD</div><h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">{completed ? "Update physical verification" : "Physical verification"}</h1><p className="mt-2 max-w-3xl text-sm text-muted">{completed ? `Creating verification version ${(verification?.latest?.version || 1) + 1}; the previous record remains immutable.` : "The first completed submission becomes immutable verification version 1."}</p></div><div className="flex flex-wrap items-center gap-2"><Badge tone={completed ? "success" : "muted"}>{completed ? `Verified v${verification?.latest?.version}` : "Not yet verified"}</Badge><Badge tone={online ? "success" : "muted"><Wifi className="mr-1 inline h-3 w-3" />{online ? "Gateway online" : "Gateway offline"}</Badge><Badge tone={gpsLive ? "success" : "muted"><Navigation className="mr-1 inline h-3 w-3" />{gpsLive ? "GPS live" : gpsWatching ? "GPS waiting" : "GPS idle"}</Badge>{live ? <button onClick={() => void stopMission()} className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-xs font-semibold text-danger"><Siren className="mr-1 inline h-3.5 w-3.5" />Stop mission</button> : <button onClick={() => void startMission()} disabled={!online || busy} className="rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:opacity-40"><ShieldCheck className="mr-1 inline h-3.5 w-3.5" />{busy ? "Starting…" : completed ? "Start update mission" : "Start SENTRY FIELD"}</button>}</div></div>
      <div className="mt-5 grid gap-3 lg:grid-cols-[1.8fr_1fr_1fr]"><Info label="Exact tender" value={tender.title} detail={tender.reference_number} /><Info label="Primary requirement" value={req.label} detail={`${req.id} · expected ${req.expected_quantity}`} /><Info label="Machine" value={tender.machine || "Normal Vision Rover"} detail={tender.demo_site || "Operator-selected site"} /></div>
      <div className="mt-4 rounded-xl border border-accent/20 bg-accent/5 p-4"><div className="text-[10px] font-semibold uppercase tracking-[.15em] text-accent">Auto-selected capabilities</div><div className="mt-3 flex flex-wrap gap-2">{capabilities.map((c) => <span key={c} className="rounded-full border border-accent/25 bg-accent/10 px-3 py-1.5 text-[11px] font-semibold text-text">{LABELS[c] || c}</span>)}</div></div>
      <div className="mt-4 rounded-xl border border-border bg-bg/20 p-3"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.14em] text-faint"><Camera className="h-3.5 w-3.5" /> Camera source</div><div className="mt-2 flex gap-2"><input value={camera} onChange={(e) => setCamera(e.target.value)} className="h-10 min-w-0 flex-1 rounded-xl border border-border bg-bg px-3 text-xs text-text" /><input aria-label="AI inference cadence" type="number" min={1} max={10} value={everyNFrames} onChange={(e) => setEveryNFrames(Math.max(1, Math.min(10, Number(e.target.value) || 1)))} className="h-10 w-24 rounded-xl border border-border bg-bg px-3 text-xs text-text" /></div><div className="mt-1.5 text-[10px] text-muted">Single DroidCam connection: FIELD gateway captures the source once, streams it to the browser, and runs AI in a separate worker.</div></div>
      {error ? <div className="mt-4 rounded-xl border border-danger/20 bg-danger/10 p-3 text-xs text-danger">{error}</div> : null}
    </section>

    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div className="flex gap-1 rounded-lg bg-surface-2 p-1"><button onClick={() => setTab("live")} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${tab === "live" ? "bg-surface text-text" : "text-muted"}`}>Live camera</button><button onClick={() => setTab("evidence")} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${tab === "evidence" ? "bg-surface text-text" : "text-muted"}`}>Evidence ({evidenceEvents.length})</button></div><div className="text-[10px] uppercase tracking-[.14em] text-faint">{status.findings} detections · {evidenceEvents.length} evidence frames</div></div>
      {tab === "live" ? <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_320px]"><div className="relative aspect-video overflow-hidden rounded-xl bg-black">{streamUrl ? <img key={streamUrl} src={streamUrl} alt="SENTRY FIELD live annotated camera" className="h-full w-full object-contain" onError={() => setError("FIELD live stream disconnected. Check the FIELD terminal and DroidCam source.")} /> : <div className="grid h-full place-items-center text-sm text-muted"><div className="text-center"><Camera className="mx-auto h-8 w-8 opacity-50" /><div className="mt-2">Start SENTRY FIELD to open the live camera.</div></div></div>}</div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] font-semibold uppercase tracking-[.15em] text-accent">AI detections</div><div className="mt-2 text-3xl font-semibold text-text">{detectionEvents.length}</div><div className="mt-1 text-xs text-muted">Event updates without blocking the camera feed.</div><div className="mt-4 space-y-2">{detectionEvents.slice(0, 8).map((e, i) => <div key={`${e.track_id || "d"}-${i}`} className="rounded-lg border border-border p-3"><div className="text-xs font-semibold text-text">{LABELS[e.capability || ""] || e.capability || "Detection"}</div><div className="mt-1 text-[10px] text-muted">{e.confidence != null ? `confidence ${(e.confidence * 100).toFixed(0)}%` : ""}{e.track_id ? ` · ${e.track_id}` : ""}</div></div>)}</div></div></div> : <div className="p-4">{evidenceEvents.length ? <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{evidenceEvents.map((e, i) => <figure key={`${e.frame_url}-${i}`} className="overflow-hidden rounded-xl border border-border bg-bg/20"><img src={evidenceUrl(e.frame_url || "")} alt={`${LABELS[e.capability || ""] || e.capability || "Detected"} evidence ${i + 1}`} className="aspect-video w-full object-cover" loading="lazy" /><figcaption className="p-3"><div className="text-xs font-semibold text-text">{LABELS[e.capability || ""] || e.capability || "Detected evidence"}</div><div className="mt-1 text-[10px] text-muted">{e.confidence != null ? `Confidence ${(e.confidence * 100).toFixed(0)}%` : "Evidence frame"}{e.gps?.lat != null && e.gps.lon != null ? ` · GPS ${e.gps.lat.toFixed(5)}, ${e.gps.lon.toFixed(5)}` : ""}</div></figcaption></figure>)}</div> : <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted"><Camera className="mx-auto h-7 w-7 opacity-60" /><div className="mt-2">No detected evidence frame yet.</div><div className="mt-1 text-xs">Move the camera over the target; one evidence frame is retained per tracked detection.</div></div>}</div>}
    </section>

    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"><div><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.15em] text-accent"><History className="h-3.5 w-3.5" /> Verification history</div><div className="mt-1 text-sm font-semibold text-text">Append-only submission record</div><div className="mt-1 text-xs text-muted">Previous versions stay immutable; deletion is disabled.</div></div>{live ? <button onClick={() => void submitVerification()} disabled={busy} className="rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:opacity-40">{busy ? "Saving…" : "Complete Verification"}</button> : null}</div><div className="mt-4 space-y-2">{verification?.history?.length ? [...verification.history].reverse().map((v) => <div key={v.id} className="flex items-center justify-between rounded-xl border border-border bg-bg/20 p-3"><div><div className="text-sm font-semibold text-text">Version {v.version} <span className="ml-2 text-[10px] uppercase tracking-wider text-accent">{v.status}</span></div><div className="mt-1 text-[10px] text-muted">{v.submitted_at || ""} · {v.evidence_count} evidence · {v.gps_evidence_count} GPS</div></div><span className="rounded-full border border-accent/20 px-2 py-1 text-[10px] font-semibold text-accent">immutable</span></div>) : <div className="rounded-xl border border-border bg-bg/20 p-4 text-sm text-muted">No submitted verification yet.</div>}</div></section>
  </main>;
}

function Info({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="rounded-xl border border-border bg-bg/20 p-4"><div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{label}</div><div className="mt-1 text-sm font-semibold leading-5 text-text">{value}</div><div className="mt-1 text-xs text-muted">{detail}</div></div>; }
