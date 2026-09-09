"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  Camera,
  CheckCircle2,
  Gauge,
  Loader2,
  MapPin,
  Navigation,
  Radar,
  ShieldCheck,
  Siren,
  Wifi,
  XCircle,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type FieldTender = {
  id: string;
  tender_id: string;
  reference_number: string;
  title: string;
  source_name: string;
  source_url: string;
  contract_location: string;
  category: string;
  machine: string;
  demo_site: string;
  requirements: Requirement[];
  verification_notes: string;
};
type EventItem = {
  type: string;
  capability?: string;
  confidence?: number;
  value?: string;
  track_id?: string | null;
  detector?: string;
  frame_url?: string | null;
  observed_at?: number;
};
type Status = {
  running: boolean;
  authorized: boolean;
  camera_url: string;
  fps: number;
  inference_ms: number;
  findings: number;
  evidence: number;
  last_detection: { type: string; confidence: number; track_id?: string | null } | null;
  last_identity: string | null;
  last_error: string | null;
  mission_id: string | null;
  requirement_id: string | null;
  tender_id: string | null;
  machine: string | null;
  demo_site: string | null;
  machine_id: string | null;
  battery: number | null;
  speed: number | null;
  gps: { status: string; source: string | null; lat: number | null; lon: number | null };
  recent_events: EventItem[];
};

const EMPTY_STATUS: Status = {
  running: false,
  authorized: false,
  camera_url: DEFAULT_CAMERA,
  fps: 0,
  inference_ms: 0,
  findings: 0,
  evidence: 0,
  last_detection: null,
  last_identity: null,
  last_error: null,
  mission_id: null,
  requirement_id: null,
  tender_id: null,
  machine: null,
  demo_site: null,
  machine_id: null,
  battery: null,
  speed: null,
  gps: { status: "unavailable", source: null, lat: null, lon: null },
  recent_events: [],
};

export function FieldHandoffConsole({ tenderKey, requirementId }: { tenderKey: string; requirementId: string }) {
  const [tender, setTender] = useState<FieldTender | null>(null);
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [online, setOnline] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatched, setDispatched] = useState(false);
  const [gpsWatching, setGpsWatching] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [cameraUrl, setCameraUrl] = useState(DEFAULT_CAMERA);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(EMPTY_STATUS);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);
  const lastPosition = useRef<{ lat: number; lon: number } | null>(null);

  const gpsLive = status.gps.status === "live" && status.gps.lat != null && status.gps.lon != null;
  const cameraLive = Boolean(streamUrl && status.running);

  const missionLabel = useMemo(() => status.mission_id || "Not started", [status.mission_id]);
  const observedRequirementEvidence = useMemo(() => {
    if (!requirement) return 0;
    if (requirement.capability === "asset_qr" || requirement.capability === "asset_text") {
      return new Set(status.recent_events.filter((e) => e.type === "identity" && e.value).map((e) => e.value)).size;
    }
    return new Set(
      status.recent_events
        .filter((e) => e.track_id && `${e.type} ${e.capability || ""}`.toLowerCase().includes(requirement.capability.replace("_", " ")))
        .map((e) => e.track_id),
    ).size;
  }, [requirement, status.recent_events]);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [healthResponse, tenderResponse] = await Promise.all([
          fetch(`${API}/health`, { cache: "no-store" }),
          fetch(`${API}/tenders/${encodeURIComponent(tenderKey)}`, { cache: "no-store" }),
        ]);
        if (!tenderResponse.ok) throw new Error("Selected field tender is unavailable");
        const payload = (await tenderResponse.json()) as FieldTender;
        if (!alive) return;
        setOnline(healthResponse.ok);
        setTender(payload);
        const selected = payload.requirements.find((item) => item.id === requirementId) ?? null;
        if (!selected) throw new Error("Selected inspection requirement is not registered for this tender");
        setRequirement(selected);
      } catch (reason) {
        if (alive) setError(reason instanceof Error ? reason.message : "Field handoff unavailable");
      }
    };
    void load();
    return () => { alive = false; };
  }, [requirementId, tenderKey]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const response = await fetch(`${API}/status`, { cache: "no-store" });
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as Status;
        if (!alive) return;
        setStatus(payload);
        setOnline(true);
        if (payload.authorized) setDispatched(true);
      } catch {
        if (alive) setOnline(false);
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 900);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    return () => {
      if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current);
      watchId.current = null;
    };
  }, []);

  async function dispatch() {
    if (!tender || !requirement) return;
    setDispatching(true);
    setError(null);
    try {
      const missionId = `${tender.id}-${requirement.id}-${Date.now()}`;
      const response = await fetch(`${API}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_id: tender.id,
          mission_id: missionId,
          requirement_id: requirement.id,
          capability: requirement.capability,
          machine: tender.machine,
          demo_site: tender.demo_site,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || `Dispatch failed (${response.status})`);
      setDispatched(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Dispatch failed");
    } finally {
      setDispatching(false);
    }
  }

  function startGps() {
    if (!("geolocation" in navigator)) {
      setGpsError("This browser does not expose device geolocation.");
      return;
    }
    if (!dispatched || !tender || !requirement) {
      setGpsError("Authorise the exact rover mission before enabling device GPS.");
      return;
    }
    setGpsError(null);
    setError(null);
    setGpsWatching(true);
    watchId.current = navigator.geolocation.watchPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        lastPosition.current = { lat, lon };
        try {
          const response = await fetch(`${API}/telemetry`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              machine_id: `browser-gps:${navigator.userAgent.slice(0, 60)}`,
              lat,
              lon,
              speed: position.coords.speed,
            }),
          });
          if (!response.ok) throw new Error(`GPS telemetry rejected (${response.status})`);
          setGpsError(null);
        } catch (reason) {
          setGpsError(reason instanceof Error ? reason.message : "Could not send GPS telemetry");
        }
      },
      (reason) => {
        setGpsWatching(false);
        setGpsError(reason.message || "Device GPS permission failed");
      },
      { enableHighAccuracy: true, maximumAge: 2500, timeout: 10000 },
    );
  }

  async function stopGps() {
    if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setGpsWatching(false);
  }

  function startCamera() {
    if (!dispatched) return setError("Dispatch the rover mission before opening the camera stream.");
    if (!gpsLive) return setError("Live device GPS is required before starting the field camera.");
    if (!cameraUrl.trim()) return setError("Camera URL is required.");
    const params = new URLSearchParams({
      camera_url: cameraUrl.trim(),
      mission_id: missionLabel,
      requirement_id: requirementId,
      capabilities: requirement?.capability || "",
      t: String(Date.now()),
    });
    setError(null);
    setStreamUrl(`${API}/stream?${params.toString()}`);
  }

  async function stopMission() {
    try { await fetch(`${API}/stop`, { method: "POST" }); }
    finally {
      setStreamUrl(null);
      await stopGps();
      setStatus((current) => ({ ...current, running: false, authorized: false }));
    }
  }

  if (error && !tender) {
    return (
      <section className="rounded-2xl border border-danger/25 bg-danger/5 p-5 shadow-sm md:p-6">
        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-danger"><XCircle className="h-3.5 w-3.5" /> Field handoff unavailable</div>
        <div className="mt-2 text-sm font-semibold text-text">{error}</div>
      </section>
    );
  }

  if (!tender || !requirement) {
    return <section className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center gap-2 text-sm text-muted"><Loader2 className="h-4 w-4 animate-spin" /> Resolving exact field requirement…</div></section>;
  }

  return (
    <main className="space-y-5">
      <section className="overflow-hidden rounded-2xl border border-accent/25 bg-surface shadow-sm">
        <div className="border-b border-border bg-accent/[0.045] px-5 py-5 md:px-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / PHASE 3</div>
              <h1 className="mt-1.5 text-2xl font-semibold tracking-tight text-text">Rover mission + live field verification</h1>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">Exact procurement context is preserved while this operator device supplies real GPS and the local gateway supplies the live camera feed.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${online ? "border-success/30 bg-success/10 text-success" : "border-border bg-surface text-muted"}`}><Wifi className="h-3 w-3" /> {online ? "Gateway online" : "Gateway offline"}</span>
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${gpsLive ? "border-success/30 bg-success/10 text-success" : "border-border bg-surface text-muted"}`}><Navigation className="h-3 w-3" /> {gpsLive ? "Phone GPS live" : "GPS not live"}</span>
              {!dispatched ? (
                <button type="button" onClick={dispatch} disabled={!online || dispatching} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-45">
                  {dispatching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                  Authorise & dispatch rover <ArrowRight className="h-3.5 w-3.5" />
                </button>
              ) : (
                <button type="button" onClick={stopMission} className="inline-flex items-center gap-2 rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-xs font-semibold text-danger"><Siren className="h-3.5 w-3.5" /> Stop mission</button>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4 md:px-6">
          <div className="rounded-xl border border-border bg-surface-2 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-faint"><ShieldCheck className="h-3.5 w-3.5 text-success" /> Tender</div><div className="mt-2 text-sm font-semibold text-text">{tender.reference_number}</div><div className="mt-1 text-xs text-muted">{tender.tender_id}</div></div>
          <div className="rounded-xl border border-accent/20 bg-accent/5 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-accent"><Radar className="h-3.5 w-3.5" /> Requirement</div><div className="mt-2 text-sm font-semibold text-text">{requirement.label}</div><div className="mt-1 text-xs text-muted">{requirement.id} · expected {requirement.expected_quantity}</div></div>
          <div className="rounded-xl border border-border bg-surface-2 p-3.5"><div className="text-[10px] uppercase tracking-[0.14em] text-faint">Machine / site</div><div className="mt-2 text-sm font-semibold text-text">{tender.machine}</div><div className="mt-1 text-xs text-muted">{tender.demo_site}</div></div>
          <div className="rounded-xl border border-border bg-surface-2 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-faint"><MapPin className="h-3.5 w-3.5" /> Contract location</div><div className="mt-2 text-sm font-semibold text-text">{tender.contract_location}</div><div className="mt-1 text-xs text-muted">{tender.category}</div></div>
        </div>

        <div className="border-t border-border px-5 py-4 md:px-6">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Mission state</div>
          <div className="mt-2 grid gap-2 md:grid-cols-4">
            <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Authorisation</div><div className="mt-1 text-sm font-semibold text-text">{dispatched ? "Granted" : "Required"}</div></div>
            <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Mission</div><div className="mt-1 truncate text-sm font-semibold text-text">{missionLabel}</div></div>
            <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">GPS</div><div className="mt-1 text-sm font-semibold text-text">{gpsLive ? `${status.gps.lat!.toFixed(5)}, ${status.gps.lon!.toFixed(5)}` : "Not received"}</div></div>
            <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Camera</div><div className="mt-1 text-sm font-semibold text-text">{cameraLive ? "Live" : "Stopped"}</div></div>
          </div>
          {!dispatched && <div className="mt-3 rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-xs text-muted">The exact tender, requirement and machine must be authorised before this operator device can publish telemetry or open the inspection stream.</div>}
        </div>
      </section>

      {dispatched && (
        <section className="grid gap-5 lg:grid-cols-[1fr_1.35fr]">
          <div className="space-y-5">
            <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3"><div><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">1 / Device positioning</div><h2 className="mt-1 text-lg font-semibold text-text">Phone GPS</h2></div><Navigation className="h-5 w-5 text-accent" /></div>
              <p className="mt-2 text-xs leading-5 text-muted">Uses the browser's real device geolocation and sends coordinates to the local SENTRY FIELD gateway. No coordinates are invented in the UI.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={gpsWatching ? stopGps : startGps} className="rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg">{gpsWatching ? "Stop GPS" : "Enable phone GPS"}</button>
                {gpsLive && <span className="inline-flex items-center gap-2 rounded-xl border border-success/25 bg-success/10 px-3 py-2.5 text-xs font-semibold text-success"><CheckCircle2 className="h-3.5 w-3.5" /> Live coordinates received</span>}
              </div>
              {gpsLive && <div className="mt-4 grid grid-cols-2 gap-2"><div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Latitude</div><div className="mt-1 text-sm font-semibold text-text">{status.gps.lat!.toFixed(6)}</div></div><div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Longitude</div><div className="mt-1 text-sm font-semibold text-text">{status.gps.lon!.toFixed(6)}</div></div></div>}
              {gpsError && <div className="mt-3 rounded-xl border border-danger/25 bg-danger/10 px-3 py-2.5 text-xs text-danger">{gpsError}</div>}
            </div>

            <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3"><div><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">2 / Visual source</div><h2 className="mt-1 text-lg font-semibold text-text">Live camera</h2></div><Camera className="h-5 w-5 text-accent" /></div>
              <label className="mt-4 block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">DroidCam / rover camera URL</span><input value={cameraUrl} onChange={(event) => setCameraUrl(event.target.value)} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50" placeholder="http://10.x.x.x:4747/video" /></label>
              <button type="button" onClick={cameraLive ? () => void stopMission() : startCamera} disabled={!gpsLive} className="mt-3 w-full rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-40">{cameraLive ? "Stop live camera" : gpsLive ? "Start live inspection feed" : "Waiting for live GPS"}</button>
              {error && <div className="mt-3 rounded-xl border border-danger/25 bg-danger/10 px-3 py-2.5 text-xs text-danger">{error}</div>}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">3 / Inspection stream</div><h2 className="mt-1 text-lg font-semibold text-text">Live field view</h2></div><div className="flex gap-2"><span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[10px] font-semibold text-muted"><Gauge className="h-3 w-3" /> {status.fps.toFixed(1)} FPS</span><span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold ${cameraLive ? "border-success/30 bg-success/10 text-success" : "border-border text-muted"}`}><Activity className="h-3 w-3" /> {cameraLive ? "LIVE" : "STOPPED"}</span></div></div>
            <div className="relative mt-4 aspect-video overflow-hidden rounded-xl bg-[#10131a]">
              {streamUrl ? <img src={streamUrl} alt="SENTRY FIELD live camera with AI annotations" className="h-full w-full object-contain" onError={() => { setError("The local gateway stream could not be read. Verify the gateway terminal and camera URL."); setStreamUrl(null); }} /> : <div className="absolute inset-0 grid place-items-center p-8 text-center"><div><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-border bg-surface-2 text-accent"><Camera className="h-6 w-6" /></div><div className="mt-4 text-sm font-semibold text-text">Camera is stopped</div><div className="mt-1 text-xs text-muted">Enable real phone GPS, then open the live inspection feed.</div></div></div>}
              <div className="absolute left-3 top-3 flex gap-2"><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold ${cameraLive ? "bg-success/90 text-bg" : "bg-bg/75 text-white"}`}><Activity className="h-3 w-3" /> {cameraLive ? "LIVE" : "OFFLINE"}</span>{gpsLive && <span className="inline-flex items-center gap-1.5 rounded-full bg-bg/75 px-2.5 py-1 text-[10px] font-semibold text-white"><MapPin className="h-3 w-3" /> GPS locked</span>}</div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.13em] text-faint">Current finding</div><div className="mt-1 flex items-center gap-2 text-sm font-semibold text-text">{status.last_detection ? <Siren className="h-3.5 w-3.5 text-accent" /> : null}{status.last_detection?.type || "None"}</div><div className="mt-1 text-xs text-muted">{status.last_detection ? `${Math.round(status.last_detection.confidence * 100)}% confidence` : "No accepted detection"}</div></div>
              <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.13em] text-faint">Captured evidence</div><div className="mt-1 text-2xl font-semibold text-text">{status.evidence}</div><div className="mt-1 text-xs text-muted">Gateway-preserved evidence events</div></div>
              <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.13em] text-faint">Requirement observations</div><div className="mt-1 text-2xl font-semibold text-text">{observedRequirementEvidence}</div><div className="mt-1 text-xs text-muted">Target expected: {requirement.expected_quantity}</div></div>
            </div>

            <div className="mt-4 rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Recent field events</div><div className="mt-2 space-y-2">{status.recent_events.filter((event) => event.type !== "telemetry").slice(0, 6).map((event, index) => <div key={`${event.type}-${event.track_id || event.value || index}`} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface px-3 py-2"><div className="min-w-0"><div className="truncate text-xs font-semibold text-text">{event.type}{event.value ? ` · ${event.value}` : ""}</div><div className="text-[10px] text-muted">{event.detector || "field gateway"}</div></div>{event.confidence != null && <span className="text-[10px] font-semibold text-accent">{Math.round(event.confidence * 100)}%</span>}</div>)}{status.recent_events.filter((event) => event.type !== "telemetry").length === 0 && <div className="py-5 text-center text-xs text-muted">No non-telemetry events yet.</div>}</div></div>
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-border bg-surface px-5 py-4 shadow-sm md:px-6">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Verification boundary</div>
        <p className="mt-1 text-xs leading-5 text-muted">{tender.verification_notes}</p>
        <p className="mt-2 text-[11px] text-muted">Phase 3 records device GPS and visual camera observations. It does not claim electrical performance, material composition, structural strength, or any other quantity that RGB imagery cannot establish.</p>
      </section>
    </main>
  );
}
