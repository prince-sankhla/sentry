"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, Camera, CheckCircle2, Navigation, Radar, Siren, Wifi, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/page";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";
const FIELD_API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";

const LABELS: Record<string, string> = {
  pothole: "Pothole",
  road_crack: "Road crack",
  streetlight: "Streetlight",
  cctv_camera: "CCTV",
  signboard: "Signboard",
  drain: "Drain / manhole",
  solar_panel: "Solar panel",
  asset_text: "OCR / asset text",
  asset_qr: "QR / asset ID",
};

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type Plan = {
  tender: { id: string; reference_number: string; title: string; source_name: string; source_url?: string | null; procuring_entity?: string | null };
  profile_id: string;
  field_tender_key: string;
  machine: string;
  demo_site: string | null;
  category: string | null;
  requirements: Requirement[];
  verification_notes: string | null;
  auto_generated?: boolean;
};
type EventItem = { type: string; capability?: string; observation?: string; confidence?: number; frame_url?: string | null; gps?: { status?: string; lat?: number | null; lon?: number | null; accuracy_m?: number | null }; mission_id?: string | null; requirement_id?: string | null; tender_id?: string | null; observed_at?: number };

export function AutoFieldMissionConsole({ tenderId }: { tenderId: string }) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [confidence, setConfidence] = useState(0.55);
  const [online, setOnline] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [gpsWatching, setGpsWatching] = useState(false);

  const capabilities = useMemo(() => Array.from(new Set((plan?.requirements || []).map((r) => r.capability).filter(Boolean))), [plan]);
  const evidence = useMemo(() => events.filter((e) => e.type === "evidence" && e.frame_url), [events]);
  const active = Boolean(streamUrl);

  useEffect(() => {
    let alive = true;
    Promise.all([
      fetch(`${BACKEND_URL}/api/investigations/tenders/${encodeURIComponent(tenderId)}/field-verification`, { cache: "no-store" }),
      fetch(`${FIELD_API}/health`, { cache: "no-store" }),
    ])
      .then(async ([planResponse, healthResponse]) => {
        if (!planResponse.ok) throw new Error(`Field plan unavailable (${planResponse.status})`);
        const payload = await planResponse.json() as Plan;
        if (alive) { setPlan(payload); setOnline(healthResponse.ok); }
      })
      .catch((reason) => alive && setError(reason instanceof Error ? reason.message : "Field plan unavailable"));
    return () => { alive = false; };
  }, [tenderId]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const response = await fetch(`${FIELD_API}/events`, { cache: "no-store" });
        if (!response.ok) throw new Error();
        const payload = await response.json() as { events?: EventItem[] };
        if (alive) {
          const rows = Array.isArray(payload.events) ? payload.events : [];
          // Preserve the DB tender identity on auto-planned evidence in the UI even
          // though the local FIELD gateway is deliberately DB-independent.
          setEvents(rows.map((event) => ({ ...event, tender_id: event.tender_id || tenderId })));
        }
      } catch { /* gateway may be offline before the mission starts */ }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 800);
    return () => { alive = false; window.clearInterval(timer); };
  }, [tenderId]);

  useEffect(() => () => { if (typeof window !== "undefined") window.clearInterval(0); }, []);

  function startGps(missionId: string) {
    if (!("geolocation" in navigator)) return;
    navigator.geolocation.watchPosition(async (position) => {
      try {
        await fetch(`${FIELD_API}/telemetry`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ machine_id: `browser-gps:${tenderId}`, lat: position.coords.latitude, lon: position.coords.longitude, speed: position.coords.speed }),
        });
        setGpsWatching(true);
      } catch { /* GPS is optional */ }
    }, () => setGpsWatching(false), { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 });
    void missionId;
  }

  async function startMission() {
    if (!plan || !capabilities.length) return;
    if (!camera.trim()) return setError("Camera URL is required.");
    try {
      setError(null);
      const requirement = plan.requirements[0];
      const missionId = `AUTO-${tenderId}-${Date.now()}`;
      const query = new URLSearchParams({ camera_url: camera.trim(), confidence: String(confidence), every_n_frames: "1", mission_id: missionId, requirement_id: requirement.id, capabilities: capabilities.join(","), t: String(Date.now()) });
      startGps(missionId);
      setStreamUrl(`${FIELD_API}/stream?${query.toString()}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Field mission could not start");
    }
  }

  if (!plan) {
    return <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm"><div className="flex items-center gap-2 text-sm text-muted">{error ? <XCircle className="h-4 w-4 text-danger" /> : <Activity className="h-4 w-4 animate-pulse text-accent" />}{error || "Resolving exact tender → automatic SENTRY FIELD plan…"}</div></section>;
  }

  return (
    <main className="space-y-5">
      <section className="rounded-2xl border border-accent/25 bg-surface p-5 shadow-sm md:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / AUTO MISSION</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">Autonomous physical verification</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">This tender had no pre-registered FIELD profile, so SENTRY generated the inspection plan automatically from the procurement record.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={online ? "success" : "muted"}><Wifi className="mr-1 inline h-3 w-3" />{online ? "Gateway online" : "Gateway offline"}</Badge>
            <Badge tone={gpsWatching ? "success" : "muted"}><Navigation className="mr-1 inline h-3 w-3" />{gpsWatching ? "GPS live" : "GPS waiting"}</Badge>
            {active ? <Badge tone="success"><CheckCircle2 className="mr-1 inline h-3 w-3" />Mission running</Badge> : <button type="button" onClick={() => void startMission()} disabled={!online} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-40"><Siren className="h-3.5 w-3.5" /> Start SENTRY FIELD</button>}
          </div>
        </div>
        <div className="mt-5 grid gap-3 lg:grid-cols-[1.6fr_1fr_1fr]">
          <div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Exact tender</div><div className="mt-1 text-sm font-semibold text-text">{plan.tender.title}</div><div className="mt-1 text-xs text-muted">{plan.tender.reference_number}</div></div>
          <div className="rounded-xl border border-accent/20 bg-accent/5 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-accent">Auto-selected capabilities</div><div className="mt-2 flex flex-wrap gap-1.5">{capabilities.map((value) => <span key={value} className="rounded-full border border-accent/20 bg-accent/10 px-2 py-1 text-[10px] font-semibold text-text">{LABELS[value] || value}</span>)}</div></div>
          <div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Mission target</div><div className="mt-1 text-sm font-semibold text-text">{plan.machine}</div><div className="mt-1 text-xs text-muted">{plan.category || "Physical procurement verification"}</div></div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_160px]"><label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Camera source</span><input value={camera} onChange={(e) => setCamera(e.target.value)} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50" /></label><label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Confidence</span><input type="number" min="0.05" max="0.99" step="0.01" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none" /></label></div>
        {error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2.5 text-xs text-danger">{error}</div>}
      </section>

      {streamUrl ? <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm"><div className="border-b border-border px-5 py-4"><div className="text-xs font-semibold uppercase tracking-[.14em] text-accent">Live camera</div><div className="mt-1 text-sm text-muted">SENTRY is running every automatically selected detector against the exact tender's inspection scope.</div></div><div className="bg-black"><img src={streamUrl} alt="SENTRY FIELD live detection stream" className="block min-h-[320px] w-full object-contain" /></div></section> : null}

      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:p-6">
        <div className="flex items-center justify-between"><div><div className="text-[10px] font-semibold uppercase tracking-[.14em] text-accent"><Camera className="mr-1 inline h-3.5 w-3.5" />Evidence</div><h2 className="mt-1 text-lg font-semibold text-text">Detected evidence frames</h2></div><span className="text-xs text-faint">{evidence.length} captured</span></div>
        {evidence.length === 0 ? <div className="mt-4 rounded-xl border border-border bg-bg/20 p-4 text-sm text-muted">No evidence frame yet. Start the mission and keep the camera pointed at the inspected asset.</div> : <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{evidence.map((item, index) => <figure key={`${item.observed_at ?? index}-${item.frame_url}`} className="overflow-hidden rounded-xl border border-border bg-bg/20"><img src={item.frame_url!.startsWith("http") ? item.frame_url! : `${FIELD_API}${item.frame_url}`} alt="Detected field evidence" className="aspect-video w-full object-cover" /><figcaption className="p-3 text-xs text-muted">{item.observation || item.capability || "Field observation"} · confidence {item.confidence != null ? item.confidence.toFixed(2) : "—"}</figcaption></figure>)}</div>}
        {plan.verification_notes && <p className="mt-4 text-[11px] leading-5 text-muted">Verification boundary: {plan.verification_notes}</p>}
      </section>

      <div className="flex items-center gap-2 text-[11px] text-faint"><ArrowRight className="h-3.5 w-3.5 text-accent" /> Current mission is an observation workflow; it does not by itself establish non-visual properties or wrongdoing.</div>
    </main>
  );
}
