"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Camera,
  CheckCircle2,
  FileText,
  Gauge,
  MapPin,
  Maximize2,
  Minimize2,
  Radar,
  Siren,
  SlidersHorizontal,
  Target,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/page";

const CAPS = [
  ["Pothole", "pothole"],
  ["Road crack", "road_crack"],
  ["Streetlight", "streetlight"],
  ["CCTV", "cctv_camera"],
  ["Signboard", "signboard"],
  ["Drain / manhole", "drain"],
  ["Solar panel", "solar_panel"],
  ["QR / asset ID", "asset_qr"],
  ["OCR", "asset_text"],
] as const;

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";

type Requirement = {
  id: string;
  capability: string;
  label: string;
  expected_quantity: number;
};

type Tender = {
  id: string;
  tender_id: string;
  reference_number: string;
  title: string;
  source_name: string;
  source_url: string;
  source_verified_on: string;
  contract_location: string;
  category: string;
  machine: string;
  demo_site: string;
  demo_expected_quantity: number;
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
  mission_id?: string | null;
  requirement_id?: string | null;
  observed_at?: number;
  frame_url?: string | null;
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
  capabilities: string[];
  confidence: number;
  every_n_frames: number;
  machine: string | null;
  demo_site: string | null;
  dispatch_at: number | null;
  machine_id: string | null;
  battery: number | null;
  speed: number | null;
  gps: { status: string; source: string | null; lat: number | null; lon: number | null };
  recent_events: EventItem[];
};

const EMPTY: Status = {
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
  capabilities: [],
  confidence: 0.65,
  every_n_frames: 2,
  machine: null,
  demo_site: null,
  dispatch_at: null,
  machine_id: null,
  battery: null,
  speed: null,
  gps: { status: "unavailable", source: null, lat: null, lon: null },
  recent_events: [],
};

function Toggle({ checked, onChange }: { checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <button
      type="button"
      aria-pressed={checked}
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 rounded-full ${checked ? "bg-accent" : "bg-bg-2"}`}
    >
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
          checked ? "left-[18px]" : "left-0.5"
        }`}
      />
    </button>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50"
      />
    </label>
  );
}

function matchesCapability(event: EventItem, capability: string) {
  const text = `${event.type} ${event.capability || ""}`.toLowerCase();
  if (capability === "pothole") return text.includes("pothole");
  if (capability === "road_crack") return text.includes("crack");
  if (capability === "streetlight") return text.includes("streetlight") || text.includes("utility pole");
  if (capability === "cctv_camera") return text.includes("cctv");
  if (capability === "signboard") return text.includes("signboard") || text.includes("road sign");
  if (capability === "drain") return text.includes("drain") || text.includes("manhole cover");
  if (capability === "solar_panel") return text.includes("solar panel");
  return false;
}

export function FieldWorkspaceCommandCenter() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [selectedReq, setSelectedReq] = useState<Requirement | null>(null);
  const [tab, setTab] = useState<"live" | "evidence" | "contract">("live");
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [mission, setMission] = useState("ST-2048");
  const [req, setReq] = useState("R-01");
  const [confidence, setConfidence] = useState(0.65);
  const [freq, setFreq] = useState(2);
  const [selected, setSelected] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(CAPS.map(([, key]) => [key, true])),
  );
  const [stream, setStream] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(EMPTY);
  const [online, setOnline] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [full, setFull] = useState(false);
  const viewer = useRef<HTMLDivElement>(null);
  const active = Boolean(stream && status.running);
  const caps = useMemo(
    () => CAPS.map(([, key]) => (selected[key] ? key : null)).filter(Boolean) as string[],
    [selected],
  );

  const observed = useMemo(() => {
    if (!selectedReq) return 0;
    if (selectedReq.capability === "asset_qr" || selectedReq.capability === "asset_text") {
      const values = new Set(
        status.recent_events
          .filter((event) => event.type === "identity" && event.value)
          .map((event) => event.value),
      );
      return values.size;
    }
    const tracks = new Set(
      status.recent_events
        .filter((event) => event.track_id && matchesCapability(event, selectedReq.capability))
        .map((event) => event.track_id),
    );
    return tracks.size;
  }, [selectedReq, status.recent_events]);

  const hasFieldEvidence = status.recent_events.some((event) => event.type === "evidence");
  const discrepancy = hasFieldEvidence ? Math.max(0, selectedReq ? selectedReq.expected_quantity - observed : 0) : null;

  useEffect(() => {
    let alive = true;
    fetch(`${API}/tenders`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Tender catalog unavailable");
        return response.json();
      })
      .then((data) => {
        if (!alive) return;
        const rows = Array.isArray(data?.tenders) ? (data.tenders as Tender[]) : [];
        setTenders(rows);
        if (rows[0]) selectTender(rows[0]);
      })
      .catch((reason: Error) => {
        if (alive) setError(reason.message);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const response = await fetch(`${API}/status`, { cache: "no-store" });
        if (!response.ok) throw new Error("Gateway offline");
        const payload = (await response.json()) as Status;
        if (alive) {
          setStatus(payload);
          setOnline(true);
        }
      } catch {
        if (alive) setOnline(false);
      }
    };
    poll();
    const id = setInterval(poll, 700);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const onFullscreen = () => setFull(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onFullscreen);
    return () => document.removeEventListener("fullscreenchange", onFullscreen);
  }, []);

  function selectTender(tender: Tender) {
    setSelectedTender(tender);
    const firstRequirement = tender.requirements[0] || null;
    setSelectedReq(firstRequirement);
    setMission(`${tender.id}-MISSION`);
    setReq(firstRequirement?.id || "REQ-01");
    setSelected(
      Object.fromEntries(CAPS.map(([, key]) => [key, Boolean(tender.requirements.some((item) => item.capability === key))])),
    );
    setError(null);
  }

  function chooseRequirement(requirement: Requirement) {
    setSelectedReq(requirement);
    setReq(requirement.id);
    setSelected((current) => ({ ...current, [requirement.capability]: true }));
    setError(null);
  }

  async function authorizeAndStart() {
    if (!selectedTender || !selectedReq) {
      setError("Select a tender and inspection requirement first.");
      return;
    }
    if (!camera.trim()) {
      setError("Camera URL is required.");
      return;
    }
    if (!caps.length) {
      setError("Select at least one capability.");
      return;
    }
    try {
      const dispatchResponse = await fetch(`${API}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_id: selectedTender.id,
          mission_id: mission.trim(),
          requirement_id: selectedReq.id,
          capability: selectedReq.capability,
          machine: selectedTender.machine,
          demo_site: selectedTender.demo_site,
        }),
      });
      if (!dispatchResponse.ok) {
        const payload = await dispatchResponse.json().catch(() => ({}));
        throw new Error(payload.detail || "Dispatch authorization failed");
      }
      const query = new URLSearchParams({
        camera_url: camera.trim(),
        confidence: String(confidence),
        every_n_frames: String(freq),
        mission_id: mission.trim(),
        requirement_id: selectedReq.id,
        capabilities: caps.join(","),
      });
      setError(null);
      setStream(`${API}/stream?${query.toString()}&t=${Date.now()}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Dispatch failed");
    }
  }

  async function stop() {
    try {
      await fetch(`${API}/stop`, { method: "POST" });
    } finally {
      setStream(null);
      setStatus((current) => ({ ...current, running: false, authorized: false }));
    }
  }

  return (
    <main className="mx-auto w-full max-w-[1900px] space-y-5">
      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent">
              <Radar className="h-3.5 w-3.5" /> SENTRY FIELD / FRONTEND COMMAND CENTER
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-text md:text-5xl">Field mission control</h1>
            <p className="mt-2 text-sm text-muted">Tender → requirement → permission → machine → inspection → evidence → contract comparison.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={online ? "success" : "muted"}>{online ? "Gateway online" : "Gateway offline"}</Badge>
            <Badge tone={status.authorized ? "success" : "muted"}>{status.authorized ? "Dispatch authorised" : "Awaiting authorisation"}</Badge>
            <button onClick={() => (active ? stop() : authorizeAndStart())} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text">
              {active ? "Stop inspection" : "Authorise & dispatch rover"}
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Tender / field mission</span>
            <select value={selectedTender?.id || ""} onChange={(event) => { const tender = tenders.find((item) => item.id === event.target.value); if (tender) selectTender(tender); }} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none">
              <option value="">Select a tender</option>
              {tenders.map((tender) => <option key={tender.id} value={tender.id}>{tender.category} — {tender.tender_id}</option>)}
            </select>
          </div>
          <Field label="Mission ID" value={mission} onChange={setMission} />
          <Field label="Requirement ID" value={req} onChange={setReq} />
        </div>

        {selectedTender && (
          <div className="mt-4 grid gap-3 xl:grid-cols-[1.7fr_1.15fr_1fr]">
            <div className="rounded-xl border border-border bg-surface-2 p-4">
              <div className="text-[10px] uppercase tracking-[.14em] text-faint">Official tender</div>
              <div className="mt-1 line-clamp-2 text-sm font-semibold text-text">{selectedTender.title}</div>
              <div className="mt-1 text-xs text-muted">{selectedTender.contract_location} · {selectedTender.source_name}</div>
              <a href={selectedTender.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-[11px] font-semibold text-accent">Open source record ↗</a>
            </div>
            <div className="rounded-xl border border-accent/20 bg-accent/5 p-4">
              <div className="text-[10px] uppercase tracking-[.14em] text-accent">Inspection requirements</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedTender.requirements.map((requirement) => (
                  <button key={requirement.id} onClick={() => chooseRequirement(requirement)} className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold ${selectedReq?.id === requirement.id ? "border-accent bg-accent/10 text-text" : "border-border text-muted"}`}>
                    {requirement.label}
                  </button>
                ))}
              </div>
              <div className="mt-2 text-xs text-muted">Machine: {selectedTender.machine} · Demo site: {selectedTender.demo_site}</div>
            </div>
            <div className="rounded-xl border border-border bg-surface-2 p-4">
              <div className="text-[10px] uppercase tracking-[.14em] text-faint">Permission gate</div>
              <div className="mt-2 flex items-center gap-2 text-sm font-semibold text-text">
                {status.authorized ? <CheckCircle2 className="h-4 w-4 text-accent" /> : <XCircle className="h-4 w-4 text-muted" />}
                {status.authorized ? "Dispatch authorised" : "Operator approval required"}
              </div>
              <div className="mt-1 text-xs text-muted">Backend validates tender, requirement, capability and machine before inspection starts.</div>
            </div>
          </div>
        )}

        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
          <div className="rounded-xl border border-border bg-surface-2 p-3">
            <div className="flex justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>Confidence threshold</span><b className="text-text">{Math.round(confidence * 100)}%</b></div>
            <input type="range" min=".05" max=".99" step=".01" value={confidence} onChange={(event) => setConfidence(Number(event.target.value))} className="mt-3 w-full" />
          </div>
          <div className="rounded-xl border border-border bg-surface-2 p-3">
            <div className="flex justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>Detection frequency</span><b className="text-text">Every {freq} frames</b></div>
            <input type="range" min="1" max="12" value={freq} onChange={(event) => setFreq(Number(event.target.value))} className="mt-3 w-full" />
          </div>
          <button onClick={authorizeAndStart} className="rounded-xl bg-accent px-5 text-xs font-semibold text-bg"><SlidersHorizontal className="mr-2 inline h-4 w-4" /> Apply & dispatch</button>
        </div>

        {error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">{error}</div>}
        {status.last_error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">Gateway: {status.last_error}</div>}
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Activity className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">State</div><div className="mt-2 text-2xl font-semibold text-text">{status.running ? "ACTIVE" : "IDLE"}</div><div className="mt-1 text-xs text-muted">gateway state</div></div>
        <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Gauge className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">FPS</div><div className="mt-2 text-2xl font-semibold text-text">{status.fps.toFixed(1)}</div><div className="mt-1 text-xs text-muted">live processing rate</div></div>
        <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Gauge className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Inference</div><div className="mt-2 text-2xl font-semibold text-text">{status.inference_ms.toFixed(0)} ms</div><div className="mt-1 text-xs text-muted">per processed frame</div></div>
        <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Siren className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Findings</div><div className="mt-2 text-2xl font-semibold text-text">{status.findings}</div><div className="mt-1 text-xs text-muted">current frame</div></div>
        <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><FileText className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Evidence</div><div className="mt-2 text-2xl font-semibold text-text">{status.evidence}</div><div className="mt-1 text-xs text-muted">persisted field events</div></div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
        <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Capability ON / OFF</div>
          <div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3"><b className="text-sm text-text">{selectedTender?.category || "No tender selected"}</b><div className="mt-1 text-xs text-muted">{selectedReq?.label || "Select an inspection requirement"}</div></div>
          <div className="mt-4 space-y-1">
            {CAPS.map(([label, key]) => <div key={key} className="flex items-center justify-between py-2"><span className={`text-xs ${selected[key] ? "text-text" : "text-muted"}`}>{label}</span><Toggle checked={Boolean(selected[key])} onChange={(value) => setSelected((current) => ({ ...current, [key]: value }))} /></div>)}
          </div>
          <div className="mt-4 rounded-xl border border-border bg-surface-2 p-3 text-xs leading-5 text-muted"><b className="text-text">Evidence policy</b><br />Visual rover evidence is observational. Specialist material, thickness, strength and electrical certification are not inferred from RGB vision.</div>
        </aside>

        <div ref={viewer} className={`min-w-0 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm ${full ? "bg-black p-3" : ""}`}>
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex gap-1 rounded-lg bg-surface-2 p-1">{(["live", "evidence", "contract"] as const).map((item) => <button key={item} onClick={() => setTab(item)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize ${tab === item ? "bg-surface text-text" : "text-muted"}`}>{item}</button>)}</div>
            <button onClick={() => (document.fullscreenElement ? document.exitFullscreen() : viewer.current?.requestFullscreen())} className="rounded-lg border border-border px-3 py-1.5 text-xs text-text">{full ? <Minimize2 className="inline h-3.5 w-3.5" /> : <Maximize2 className="inline h-3.5 w-3.5" />} Fullscreen</button>
          </div>

          {tab === "live" && (
            <div className="p-3">
              <div className={`relative overflow-hidden rounded-xl bg-[#0b0e13] ${full ? "h-[calc(100vh-58px)]" : "min-h-[55vh] xl:min-h-[68vh]"}`}>
                {stream ? <img src={stream} alt="SENTRY FIELD annotated live inspection" className="h-full w-full object-contain" onError={() => { setError("Cannot read gateway stream. Check camera URL and local gateway."); void stop(); }} /> : <div className="absolute inset-0 grid place-items-center text-center"><div><Camera className="mx-auto h-10 w-10 text-accent" /><div className="mt-3 font-semibold text-text">Inspection stopped</div><div className="mt-1 text-xs text-muted">Select tender → requirement → authorize → dispatch.</div></div></div>}
                <div className="absolute left-4 top-4 flex flex-wrap gap-2"><Badge tone={active ? "success" : "muted"}>{active ? "LIVE" : "OFFLINE"}</Badge>{status.mission_id && <Badge tone="muted">Mission {status.mission_id}</Badge>}{status.demo_site && <Badge tone="muted">{status.demo_site}</Badge>}</div>
                <div className="absolute bottom-4 left-4 flex flex-wrap gap-2"><Badge tone="muted"><MapPin className="mr-1 inline h-3 w-3" />GPS {status.gps.status}</Badge>{status.machine_id && <Badge tone="muted">Machine {status.machine_id}</Badge>}{status.last_identity && <Badge tone="success">ID {status.last_identity.slice(0, 45)}</Badge>}</div>
              </div>
            </div>
          )}

          {tab === "evidence" && (
            <div className="divide-y divide-border">
              {status.recent_events.filter((event) => event.type === "evidence" || event.type === "identity" || event.type === "dispatch").length ? status.recent_events.filter((event) => event.type === "evidence" || event.type === "identity" || event.type === "dispatch").map((event, index) => (
                <div key={`${event.observed_at || index}`} className="grid gap-3 p-4 md:grid-cols-[110px_1fr]">
                  {event.frame_url ? <a href={`${API}${event.frame_url}`} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-border bg-bg-2"><img src={`${API}${event.frame_url}`} alt="SENTRY evidence frame" className="aspect-video h-full w-full object-cover" /></a> : <div className="grid aspect-video place-items-center rounded-lg border border-border bg-bg-2 text-[10px] text-faint">No frame</div>}
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-text">{event.capability || event.type}</span>{typeof event.confidence === "number" && <Badge tone="muted">{Math.round(event.confidence * 100)}% confidence</Badge>}</div>
                    <div className="mt-1 text-xs text-muted">{event.detector || "field pipeline"} · {event.track_id || "no track"}</div>
                    <div className="mt-2 text-[11px] text-faint">{event.mission_id || "No mission"} · {event.requirement_id || "No requirement"}</div>
                  </div>
                </div>
              )) : <div className="p-10 text-center text-sm text-muted">Evidence will appear here when an accepted finding is persisted.</div>}
            </div>
          )}

          {tab === "contract" && (
            <div className="grid gap-4 p-5 md:grid-cols-3">
              <div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Expected</div><div className="mt-2 text-3xl font-semibold text-text">{selectedReq?.expected_quantity ?? "—"}</div><div className="mt-1 text-xs text-muted">contract requirement</div></div>
              <div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Observed</div><div className="mt-2 text-3xl font-semibold text-text">{hasFieldEvidence ? observed : "—"}</div><div className="mt-1 text-xs text-muted">mission-scoped tracks</div></div>
              <div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Discrepancy</div><div className="mt-2 text-3xl font-semibold text-text">{discrepancy === null ? "—" : discrepancy}</div><div className="mt-1 text-xs text-muted">needs investigation if non-zero</div></div>
              <div className="md:col-span-3 rounded-xl border border-accent/20 bg-accent/5 p-4 text-xs leading-6 text-muted"><Target className="mr-2 inline h-4 w-4 text-accent" /><b className="text-text">Interpretation:</b> A discrepancy is a verification trigger, not a finding of misconduct. Validate variations, outages, maintenance, survey error and other legitimate explanations before escalation.</div>
            </div>
          )}
        </div>

        <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Mission chain</div>
          <div className="mt-3 space-y-2 text-xs text-muted">
            {[
              ["Tender", selectedTender?.tender_id || "—"],
              ["Requirement", selectedReq?.label || "—"],
              ["Machine", selectedTender?.machine || "—"],
              ["Mission", mission || "—"],
              ["Camera", camera || "—"],
            ].map(([label, value]) => <div key={label} className="flex items-start justify-between gap-3 rounded-lg border border-border bg-surface-2 px-3 py-2"><span className="text-faint">{label}</span><span className="max-w-[190px] text-right text-text">{value}</span></div>)}
          </div>
          <div className="mt-4 rounded-xl border border-border bg-surface-2 p-3 text-xs text-muted"><b className="text-text">Ground truth</b><br />Camera evidence is linked to the selected tender, requirement and mission. GPS becomes live only when telemetry supplies coordinates.</div>
        </aside>
      </section>
    </main>
  );
}
