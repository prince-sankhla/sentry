"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Camera, CheckCircle2, FileText, Gauge, MapPin, Maximize2, Minimize2, Radar, Siren, SlidersHorizontal, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/page";

const CAPS = [
  ["Pothole", "pothole"], ["Road crack", "road_crack"], ["Streetlight", "streetlight"],
  ["CCTV", "cctv_camera"], ["Signboard", "signboard"], ["Drain / manhole", "drain"],
  ["Solar panel", "solar_panel"], ["QR / asset ID", "asset_qr"], ["OCR", "asset_text"],
] as const;

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const DEFAULT_CAMERA = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://127.0.0.1:4747/video";

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type Tender = {
  id: string; tender_id: string; reference_number?: string; title: string; source_name: string; source_url: string;
  source_verified_on?: string; contract_location: string; category: string; machine: string; demo_site: string;
  demo_expected_quantity?: number; requirements: Requirement[]; verification_notes: string;
};
type EventItem = {
  type: string; capability?: string; confidence?: number; value?: string; track_id?: string | null; detector?: string;
  mission_id?: string | null; requirement_id?: string | null; tender_id?: string | null; observed_at?: number; frame_url?: string | null;
};
type Status = {
  running: boolean; authorized: boolean; camera_url: string; fps: number; inference_ms: number; findings: number; evidence: number;
  last_detection: { type: string; confidence: number; track_id?: string | null } | null; last_identity: string | null; last_error: string | null;
  mission_id: string | null; requirement_id: string | null; tender_id: string | null; capabilities: string[]; confidence: number;
  every_n_frames: number; machine: string | null; demo_site: string | null; dispatch_at: number | null; machine_id: string | null;
  battery: number | null; speed: number | null; gps: { status: string; source: string | null; lat: number | null; lon: number | null }; recent_events: EventItem[];
};
const EMPTY: Status = {
  running: false, authorized: false, camera_url: DEFAULT_CAMERA, fps: 0, inference_ms: 0, findings: 0, evidence: 0,
  last_detection: null, last_identity: null, last_error: null, mission_id: null, requirement_id: null, tender_id: null,
  capabilities: [], confidence: 0.65, every_n_frames: 3, machine: null, demo_site: null, dispatch_at: null, machine_id: null,
  battery: null, speed: null, gps: { status: "unavailable", source: null, lat: null, lon: null }, recent_events: [],
};

function Field({ label, value, onChange, type = "text" }: { label: string; value: string | number; onChange: (value: string) => void; type?: string }) {
  return <label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{label}</span><input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50" /></label>;
}
function Toggle({ checked, onChange }: { checked: boolean; onChange: (value: boolean) => void }) {
  return <button type="button" aria-pressed={checked} onClick={() => onChange(!checked)} className={`relative h-5 w-9 rounded-full ${checked ? "bg-accent" : "bg-bg-2"}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? "left-[18px]" : "left-0.5"}`} /></button>;
}
function matchCapability(event: EventItem, capability: string) {
  const text = `${event.type} ${event.capability || ""}`.toLowerCase();
  if (capability === "pothole") return text.includes("pothole");
  if (capability === "road_crack") return text.includes("crack");
  if (capability === "streetlight") return text.includes("streetlight") || text.includes("utility pole");
  if (capability === "cctv_camera") return text.includes("cctv");
  if (capability === "signboard") return text.includes("signboard") || text.includes("road sign");
  if (capability === "drain") return text.includes("drain") || text.includes("manhole");
  if (capability === "solar_panel") return text.includes("solar panel");
  return false;
}
function evidenceUrl(url: string | null | undefined) {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API}${url}`;
}

export function FieldWorkspaceCommandCenter() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [selectedReq, setSelectedReq] = useState<Requirement | null>(null);
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [mission, setMission] = useState("ST-2048");
  const [req, setReq] = useState("REQ-01");
  const [confidence, setConfidence] = useState(0.65);
  const [freq, setFreq] = useState(3);
  const [selected, setSelected] = useState<Record<string, boolean>>(() => Object.fromEntries(CAPS.map(([, k]) => [k, true])));
  const [tab, setTab] = useState<"live" | "evidence" | "contract">("live");
  const [stream, setStream] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(EMPTY);
  const [online, setOnline] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [full, setFull] = useState(false);
  const viewer = useRef<HTMLDivElement>(null);
  const active = Boolean(stream && status.running);
  const caps = useMemo(() => CAPS.map(([, k]) => selected[k] ? k : null).filter(Boolean) as string[], [selected]);
  const evidenceEvents = useMemo(() => status.recent_events.filter((e) => e.type === "evidence" && e.frame_url), [status.recent_events]);
  const observed = useMemo(() => {
    if (!selectedReq) return 0;
    if (selectedReq.capability === "asset_qr" || selectedReq.capability === "asset_text") return new Set(status.recent_events.filter((e) => e.type === "identity" && e.value).map((e) => e.value)).size;
    return new Set(status.recent_events.filter((e) => e.track_id && matchCapability(e, selectedReq.capability)).map((e) => e.track_id)).size;
  }, [selectedReq, status.recent_events]);
  const discrepancy = status.evidence > 0 && selectedReq ? Math.max(0, selectedReq.expected_quantity - observed) : null;

  useEffect(() => {
    let alive = true;
    fetch(`${API}/tenders`, { cache: "no-store" }).then((r) => { if (!r.ok) throw new Error("Tender catalog unavailable"); return r.json(); }).then((data) => {
      if (!alive) return; const rows = Array.isArray(data?.tenders) ? data.tenders as Tender[] : []; setTenders(rows); if (rows[0]) selectTender(rows[0]);
    }).catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try { const r = await fetch(`${API}/status`, { cache: "no-store" }); if (!r.ok) throw new Error(); const payload = await r.json() as Status; if (alive) { setStatus(payload); setOnline(true); } }
      catch { if (alive) setOnline(false); }
    };
    void poll(); const id = window.setInterval(() => void poll(), 600); return () => { alive = false; window.clearInterval(id); };
  }, []);
  useEffect(() => { const onFullscreen = () => setFull(Boolean(document.fullscreenElement)); document.addEventListener("fullscreenchange", onFullscreen); return () => document.removeEventListener("fullscreenchange", onFullscreen); }, []);

  function selectTender(tender: Tender) {
    const first = tender.requirements[0] || null;
    setSelectedTender(tender); setSelectedReq(first); setMission(`${tender.id}-MISSION`); setReq(first?.id || "REQ-01");
    setSelected(Object.fromEntries(CAPS.map(([, k]) => [k, Boolean(tender.requirements.some((r) => r.capability === k))]))); setError(null);
  }
  function chooseRequirement(requirement: Requirement) { setSelectedReq(requirement); setReq(requirement.id); setSelected((current) => ({ ...current, [requirement.capability]: true })); setError(null); }
  async function authorizeAndStart() {
    if (!selectedTender || !selectedReq) return setError("Select a tender and inspection requirement first.");
    if (!camera.trim()) return setError("Camera URL is required.");
    if (!caps.length) return setError("Select at least one capability.");
    try {
      const dispatch = await fetch(`${API}/dispatch`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tender_id: selectedTender.id, mission_id: mission.trim(), requirement_id: selectedReq.id, capability: selectedReq.capability, machine: selectedTender.machine, demo_site: selectedTender.demo_site }) });
      if (!dispatch.ok) { const p = await dispatch.json().catch(() => ({})); throw new Error(p.detail || "Dispatch authorization failed"); }
      const query = new URLSearchParams({ camera_url: camera.trim(), confidence: String(confidence), every_n_frames: String(freq), mission_id: mission.trim(), requirement_id: selectedReq.id, capabilities: caps.join(",") });
      setError(null); setTab("live"); setStream(`${API}/stream?${query.toString()}&t=${Date.now()}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Dispatch failed"); }
  }
  async function stop() { try { await fetch(`${API}/stop`, { method: "POST" }); } finally { setStream(null); setStatus((s) => ({ ...s, running: false, authorized: false })); } }

  return <main className="mx-auto w-full max-w-[1900px] space-y-5">
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div><div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / FRONTEND COMMAND CENTER</div><h1 className="text-3xl font-semibold tracking-tight text-text md:text-5xl">Field mission control</h1><p className="mt-2 text-sm text-muted">Tender → requirement → permission → machine → inspection → evidence → contract comparison.</p></div>
        <div className="flex flex-wrap items-center gap-2"><Badge tone={online ? "success" : "muted"}>{online ? "Gateway online" : "Gateway offline"}</Badge><Badge tone={status.authorized ? "success" : "muted"}>{status.authorized ? "Dispatch authorised" : "Awaiting authorisation"}</Badge><button onClick={() => active ? void stop() : void authorizeAndStart()} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text">{active ? "Stop inspection" : "Authorise & dispatch rover"}</button></div>
      </div>
      <div className="mt-5 grid gap-3 xl:grid-cols-[1.25fr_.9fr_.9fr]">
        <div><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Tender / field mission</span><select value={selectedTender?.id || ""} onChange={(e) => { const t = tenders.find((x) => x.id === e.target.value); if (t) selectTender(t); }} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none"><option value="">Select a tender</option>{tenders.map((t) => <option key={t.id} value={t.id}>{t.category} — {t.tender_id}</option>)}</select></div>
        <Field label="Mission ID" value={mission} onChange={setMission} /><Field label="Requirement ID" value={req} onChange={setReq} />
      </div>
      <div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.14em] text-accent"><Camera className="h-3.5 w-3.5" /> Camera source</div><div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto]"><input value={camera} onChange={(e) => setCamera(e.target.value)} aria-label="Camera URL" placeholder="http://10.x.x.x:4747/video" className="h-11 w-full rounded-xl border border-border bg-bg px-3 text-xs text-text outline-none focus:border-accent/60" /><button onClick={() => setCamera(camera.trim())} className="rounded-xl border border-border px-4 text-xs font-semibold text-text">Apply camera URL</button></div><div className="mt-1.5 text-[11px] text-muted">DroidCam / local rover camera URL · {DEFAULT_CAMERA}</div></div>
      {selectedTender && <div className="mt-4 grid gap-3 xl:grid-cols-[1.6fr_1.2fr_1fr]"><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Official tender</div><div className="mt-1 line-clamp-2 text-sm font-semibold text-text">{selectedTender.title}</div><div className="mt-1 text-xs text-muted">{selectedTender.contract_location} · {selectedTender.source_name}</div><a href={selectedTender.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-[11px] font-semibold text-accent">Open source record ↗</a></div><div className="rounded-xl border border-accent/20 bg-accent/5 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-accent">Inspection requirements</div><div className="mt-2 flex flex-wrap gap-2">{selectedTender.requirements.map((r) => <button key={r.id} onClick={() => chooseRequirement(r)} className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold ${selectedReq?.id === r.id ? "border-accent bg-accent/10 text-text" : "border-border text-muted"}`}>{r.label}</button>)}</div><div className="mt-2 text-xs text-muted">Machine: {selectedTender.machine} · Demo site: {selectedTender.demo_site}</div></div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Permission gate</div><div className="mt-2 flex items-center gap-2 text-sm font-semibold text-text">{status.authorized ? <CheckCircle2 className="h-4 w-4 text-accent" /> : <XCircle className="h-4 w-4 text-muted" />}{status.authorized ? "Dispatch authorised" : "Operator approval required"}</div><div className="mt-1 text-xs text-muted">Backend validates tender, requirement, capability and machine.</div></div></div>}
      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr_auto]"><div className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>Confidence</span><b className="text-text">{Math.round(confidence * 100)}%</b></div><input type="range" min=".05" max=".99" step=".01" value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} className="mt-3 w-full" /></div><div className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>Detection frequency</span><b className="text-text">Every {freq} frames</b></div><input type="range" min="1" max="12" value={freq} onChange={(e) => setFreq(Number(e.target.value))} className="mt-3 w-full" /></div><button onClick={() => void authorizeAndStart()} className="rounded-xl bg-accent px-5 text-xs font-semibold text-bg"><SlidersHorizontal className="mr-2 inline h-4 w-4" /> Apply & dispatch</button></div>
      {error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">{error}</div>}{status.last_error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">Gateway: {status.last_error}</div>}
    </section>
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Activity className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">State</div><div className="mt-2 text-2xl font-semibold text-text">{status.running ? "ACTIVE" : "IDLE"}</div><div className="mt-1 text-xs text-muted">gateway state</div></div>
      <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Gauge className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">FPS</div><div className="mt-2 text-2xl font-semibold text-text">{status.fps.toFixed(1)}</div><div className="mt-1 text-xs text-muted">live processing rate</div></div>
      <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Gauge className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Inference</div><div className="mt-2 text-2xl font-semibold text-text">{status.inference_ms.toFixed(0)} ms</div><div className="mt-1 text-xs text-muted">processed frame time</div></div>
      <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Siren className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Findings</div><div className="mt-2 text-2xl font-semibold text-text">{status.findings}</div><div className="mt-1 text-xs text-muted">current live findings</div></div>
      <button type="button" onClick={() => setTab("evidence")} className={`rounded-2xl border p-4 text-left shadow-sm transition ${tab === "evidence" ? "border-accent/50 bg-accent/5" : "border-border bg-surface hover:border-accent/30"}`}><FileText className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">Evidence</div><div className="mt-2 text-2xl font-semibold text-text">{status.evidence}</div><div className="mt-1 text-xs text-muted">Click to inspect captured images →</div></button>
    </section>
    <section className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Capability ON / OFF</div><div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3"><b className="text-sm text-text">{selectedTender?.category || "No tender selected"}</b><div className="mt-1 text-xs text-muted">{selectedReq?.label || "Select an inspection requirement"}</div></div><div className="mt-4 space-y-1">{CAPS.map(([label, key]) => <div key={key} className="flex items-center justify-between py-2"><span className={`text-xs ${selected[key] ? "text-text" : "text-muted"}`}>{label}</span><Toggle checked={Boolean(selected[key])} onChange={(v) => setSelected((cur) => ({ ...cur, [key]: v }))} /></div>)}</div><div className="mt-4 rounded-xl border border-border bg-surface-2 p-3 text-xs leading-5 text-muted"><b className="text-text">Evidence policy</b><br />Visual evidence is observational. Material, thickness, strength and electrical certification are not inferred from RGB vision.</div></aside>
      <div ref={viewer} className={`min-w-0 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm ${full ? "bg-black p-3" : ""}`}>
        <div className="flex items-center justify-between border-b border-border px-4 py-3"><div className="flex gap-1 rounded-lg bg-surface-2 p-1">{(["live", "evidence", "contract"] as const).map((t) => <button key={t} onClick={() => setTab(t)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize ${tab === t ? "bg-surface text-text" : "text-muted"}`}>{t}</button>)}</div><button onClick={() => (document.fullscreenElement ? document.exitFullscreen() : viewer.current?.requestFullscreen())} className="rounded-lg border border-border px-3 py-1.5 text-xs text-text">{full ? <Minimize2 className="inline h-3.5 w-3.5" /> : <Maximize2 className="inline h-3.5 w-3.5" />} Fullscreen</button></div>
        {tab === "live" && <div className="p-3"><div className={`relative overflow-hidden rounded-xl bg-[#0b0e13] ${full ? "h-[calc(100vh-58px)]" : "min-h-[55vh] xl:min-h-[68vh]"}`}>{stream ? <img src={stream} alt="SENTRY FIELD annotated live inspection" className="h-full w-full object-contain" onError={() => { setError("Cannot read gateway stream. Check camera URL and gateway."); void stop(); }} /> : <div className="absolute inset-0 grid place-items-center text-center"><div><Camera className="mx-auto h-10 w-10 text-accent" /><div className="mt-3 font-semibold text-text">Inspection stopped</div><div className="mt-1 text-xs text-muted">Set Camera URL → select tender/requirement → dispatch.</div></div></div>}<div className="absolute left-4 top-4 flex flex-wrap gap-2"><Badge tone={active ? "success" : "muted"}>{active ? "LIVE" : "OFFLINE"}</Badge>{status.mission_id && <Badge tone="muted">Mission {status.mission_id}</Badge>}</div><div className="absolute bottom-4 left-4 flex flex-wrap gap-2"><Badge tone="muted"><MapPin className="mr-1 inline h-3 w-3" />GPS {status.gps.status}</Badge>{status.last_identity && <Badge tone="success">ID {status.last_identity.slice(0, 40)}</Badge>}</div></div></div>}
        {tab === "evidence" && <div className="p-4">{evidenceEvents.length === 0 ? <div className="p-8 text-center text-sm text-muted">No captured evidence yet. Start inspection and wait for a finding.</div> : <div className="space-y-3">{evidenceEvents.map((e, i) => { const src = evidenceUrl(e.frame_url); return <article key={`${e.track_id || "ev"}-${e.observed_at || i}`} className="overflow-hidden rounded-2xl border border-border bg-surface-2"><div className="grid gap-4 p-3 md:grid-cols-[260px_1fr]">{src ? <a href={src} target="_blank" rel="noreferrer" className="block"><img src={src} alt={`${e.capability || e.type} captured evidence`} className="h-44 w-full rounded-xl border border-border bg-black object-cover" /></a> : <div className="h-44 rounded-xl border border-border bg-black" />}<div className="min-w-0"><div className="flex items-center justify-between gap-2"><div className="text-sm font-semibold text-text">{e.capability || e.type}</div><Badge tone="success">Captured</Badge></div><div className="mt-2 grid gap-2 text-xs"><div><span className="text-faint">Tender:</span> <span className="text-text">{e.tender_id || selectedTender?.id || "—"}</span></div><div><span className="text-faint">Tender title:</span> <span className="text-text">{selectedTender?.title || "Field inspection tender"}</span></div><div><span className="text-faint">Requirement:</span> <span className="text-text">{e.requirement_id || "—"}</span></div><div><span className="text-faint">Confidence:</span> <span className="text-text">{Math.round((e.confidence || 0) * 100)}%</span></div><div><span className="text-faint">Detector:</span> <span className="text-text">{e.detector || "vision"}</span></div></div><div className="mt-3 text-[11px] text-muted">Open image ↗ to inspect the original captured frame.</div></div></div></article>; })}</div>}</div>}
        {tab === "contract" && <div className="p-4">{selectedReq ? <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Expected</div><div className="mt-2 text-3xl font-semibold text-text">{selectedReq.expected_quantity}</div></div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Observed</div><div className="mt-2 text-3xl font-semibold text-text">{observed}</div></div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Discrepancy</div><div className="mt-2 text-3xl font-semibold text-text">{discrepancy === null ? "—" : discrepancy}</div></div><div className="sm:col-span-3 rounded-xl border border-border bg-surface-2 p-4 text-sm text-muted"><b className="text-text">Requirement:</b> {selectedReq.label}. Visual evidence supports observation; it does not by itself establish non-compliance or fraud.</div></div> : <div className="p-8 text-center text-sm text-muted">Select an inspection requirement first.</div>}</div>}
      </div>
      <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Mission state</div><div className="mt-3 space-y-3 text-xs"><div className="flex justify-between gap-3"><span className="text-muted">Camera</span><span className="max-w-[190px] truncate text-text">{camera}</span></div><div className="flex justify-between"><span className="text-muted">Requirement</span><span className="text-text">{selectedReq?.id || "—"}</span></div><div className="flex justify-between"><span className="text-muted">Machine</span><span className="text-text">{status.machine || selectedTender?.machine || "—"}</span></div><div className="flex justify-between"><span className="text-muted">GPS</span><span className="text-text">{status.gps.status}</span></div><div className="flex justify-between"><span className="text-muted">Battery</span><span className="text-text">{status.battery == null ? "—" : `${status.battery}%`}</span></div></div><div className="mt-5 rounded-xl border border-border bg-surface-2 p-3 text-xs leading-5 text-muted"><b className="text-text">Last detection</b><br />{status.last_detection ? `${status.last_detection.type} · ${Math.round(status.last_detection.confidence * 100)}%` : "No accepted detection"}</div><button type="button" onClick={() => setTab("evidence")} className="mt-3 w-full rounded-xl border border-accent/20 bg-accent/5 p-3 text-left text-xs leading-5 text-muted hover:border-accent/40"><b className="text-text">Evidence gallery</b><br />{status.evidence} captured frame{status.evidence === 1 ? "" : "s"} · Click to inspect images and tender provenance.</button></aside>
    </section>
  </main>;
}
