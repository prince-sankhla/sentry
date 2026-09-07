"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Camera, CheckCircle2, FileText, Gauge, MapPin, Maximize2, Minimize2, Radar, Siren, SlidersHorizontal, Target, XCircle } from "lucide-react";
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
  id: string; tender_id: string; reference_number: string; title: string; source_name: string;
  source_url: string; source_verified_on: string; contract_location: string; category: string;
  machine: string; demo_site: string; demo_expected_quantity: number; requirements: Requirement[];
  verification_notes: string;
};
type EventItem = { type: string; confidence?: number; value?: string; track_id?: string | null; detector?: string; mission_id?: string | null; requirement_id?: string | null; observed_at?: number };
type Status = {
  running: boolean; camera_url: string; fps: number; inference_ms: number; findings: number; evidence: number;
  last_detection: any; last_identity: string | null; last_error: string | null; mission_id: string | null;
  requirement_id: string | null; capabilities: string[]; confidence: number; every_n_frames: number;
  gps: { status: string; source: string | null; lat: number | null; lon: number | null }; recent_events: EventItem[];
};
const EMPTY: Status = {
  running: false, camera_url: DEFAULT_CAMERA, fps: 0, inference_ms: 0, findings: 0, evidence: 0,
  last_detection: null, last_identity: null, last_error: null, mission_id: null, requirement_id: null,
  capabilities: [], confidence: .65, every_n_frames: 3,
  gps: { status: "unavailable", source: null, lat: null, lon: null }, recent_events: [],
};

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return <button type="button" aria-pressed={checked} onClick={() => onChange(!checked)} className={`relative h-5 w-9 rounded-full ${checked ? "bg-accent" : "bg-bg-2"}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${checked ? "left-[18px]" : "left-0.5"}`} /></button>;
}
function Field({ label, value, onChange, type = "text" }: { label: string; value: string | number; onChange: (v: string) => void; type?: string }) {
  return <label className="block"><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{label}</span><input type={type} value={value} onChange={e => onChange(e.target.value)} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none focus:border-accent/50" /></label>;
}

export function FieldWorkspaceCommandCenter() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [selectedReq, setSelectedReq] = useState<Requirement | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [tab, setTab] = useState<"live" | "evidence" | "contract">("live");
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [mission, setMission] = useState("ST-2048");
  const [req, setReq] = useState("R-01");
  const [confidence, setConfidence] = useState(.65);
  const [freq, setFreq] = useState(3);
  const [expected, setExpected] = useState(6);
  const [selected, setSelected] = useState<Record<string, boolean>>(() => Object.fromEntries(CAPS.map(([, k]) => [k, true])));
  const [stream, setStream] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(EMPTY);
  const [online, setOnline] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [full, setFull] = useState(false);
  const viewer = useRef<HTMLDivElement>(null);
  const active = Boolean(stream && status.running);
  const caps = useMemo(() => CAPS.map(([, k]) => selected[k] ? k : null).filter(Boolean) as string[], [selected]);

  const observed = useMemo(() => {
    const relevant = selectedReq?.capability || "streetlight";
    const needle = relevant === "cctv_camera" ? "cctv" : relevant === "road_crack" ? "crack" : relevant.replace("asset_", "");
    return new Set(status.recent_events.filter(e => e.track_id && e.type.toLowerCase().includes(needle)).map(e => e.track_id)).size;
  }, [status.recent_events, selectedReq]);
  const discrepancy = Math.max(0, expected - observed);

  useEffect(() => {
    let alive = true;
    fetch(`${API}/tenders`, { cache: "no-store" }).then(r => r.json()).then(data => {
      if (!alive) return;
      const rows = Array.isArray(data?.tenders) ? data.tenders as Tender[] : [];
      setTenders(rows);
      if (rows[0]) selectTender(rows[0]);
    }).catch(() => {});
    return () => { alive = false; };
  }, []);
  useEffect(() => { const onFs = () => setFull(Boolean(document.fullscreenElement)); document.addEventListener("fullscreenchange", onFs); return () => document.removeEventListener("fullscreenchange", onFs); }, []);
  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try { const r = await fetch(`${API}/status`, { cache: "no-store" }); if (!r.ok) throw new Error(); const p = await r.json() as Status; if (alive) { setStatus(p); setOnline(true); } }
      catch { if (alive) setOnline(false); }
    };
    poll(); const id = setInterval(poll, 700); return () => { alive = false; clearInterval(id); };
  }, []);

  function selectTender(t: Tender) {
    setSelectedTender(t);
    const r = t.requirements[0] || null;
    setSelectedReq(r);
    setMission(`${t.id}-MISSION`);
    setReq(r?.id || "REQ-01");
    setExpected(r?.expected_quantity || t.demo_expected_quantity);
    const requirementCaps = new Set(t.requirements.map(x => x.capability));
    setSelected(Object.fromEntries(CAPS.map(([, k]) => [k, requirementCaps.has(k)])));
    setAuthorized(false);
    setError(null);
  }
  function chooseRequirement(r: Requirement) {
    setSelectedReq(r); setReq(r.id); setExpected(r.expected_quantity);
    setSelected(s => ({ ...s, [r.capability]: true })); setAuthorized(false);
  }
  function authorizeAndStart() {
    if (!selectedTender || !selectedReq) { setError("Select a tender requirement first."); return; }
    if (!camera.trim()) { setError("Camera URL is required"); return; }
    if (!caps.length) { setError("Select at least one capability"); return; }
    setAuthorized(true); setError(null);
    const q = new URLSearchParams({ camera_url: camera.trim(), confidence: String(confidence), every_n_frames: String(freq), mission_id: mission.trim(), requirement_id: req.trim(), capabilities: caps.join(",") });
    setStream(`${API}/stream?${q.toString()}&t=${Date.now()}`);
  }
  async function stop() { try { await fetch(`${API}/stop`, { method: "POST" }); } catch {} setStream(null); setAuthorized(false); setStatus(s => ({ ...s, running: false })); }

  return <main className="mx-auto w-full max-w-[1900px] space-y-5">
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / FRONTEND COMMAND CENTER</div><h1 className="text-3xl font-semibold tracking-tight text-text md:text-5xl">Field mission control</h1><p className="mt-2 text-sm text-muted">Tender → requirement → permission → machine → inspection → evidence → contract comparison.</p></div><div className="flex flex-wrap items-center gap-2"><Badge tone={online ? "success" : "muted"}>{online ? "Gateway online" : "Gateway offline"}</Badge><Badge tone={authorized ? "success" : "muted"}>{authorized ? "Operator authorised" : "Awaiting authorisation"}</Badge><button onClick={() => active ? stop() : authorizeAndStart()} className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text">{active ? "Stop inspection" : "Authorise & dispatch rover"}</button></div></div>
      <div className="mt-5 grid gap-3 xl:grid-cols-[1.4fr_1fr_1fr]"><div><span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Tender / field mission</span><select value={selectedTender?.id || ""} onChange={e => { const t = tenders.find(x => x.id === e.target.value); if (t) selectTender(t); }} className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none"><option value="">Select a tender</option>{tenders.map(t => <option key={t.id} value={t.id}>{t.category} — {t.tender_id}</option>)}</select></div><Field label="Mission ID" value={mission} onChange={setMission} /><Field label="Requirement ID" value={req} onChange={setReq} /></div>
      {selectedTender && <div className="mt-4 grid gap-3 xl:grid-cols-[1.7fr_1.15fr_1fr]"><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Official tender</div><div className="mt-1 line-clamp-2 text-sm font-semibold text-text">{selectedTender.title}</div><div className="mt-1 text-xs text-muted">{selectedTender.contract_location} · {selectedTender.source_name}</div><a href={selectedTender.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-[11px] font-semibold text-accent">Open source record ↗</a></div><div className="rounded-xl border border-accent/20 bg-accent/5 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-accent">Inspection requirements</div><div className="mt-2 flex flex-wrap gap-2">{selectedTender.requirements.map(r => <button key={r.id} onClick={() => chooseRequirement(r)} className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold ${selectedReq?.id === r.id ? "border-accent bg-accent/10 text-text" : "border-border text-muted"}`}>{r.label}</button>)}</div><div className="mt-2 text-xs text-muted">Machine: {selectedTender.machine} · Demo site: {selectedTender.demo_site}</div></div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Permission gate</div><div className="mt-2 flex items-center gap-2 text-sm font-semibold text-text">{authorized ? <CheckCircle2 className="h-4 w-4 text-accent" /> : <XCircle className="h-4 w-4 text-muted" />}{authorized ? "Dispatch authorised" : "Operator approval required"}</div><div className="mt-1 text-xs text-muted">One click creates a mission-scoped inspection request for the selected requirement.</div></div></div>}
      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr_auto]"><div className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>Confidence threshold</span><b className="text-text">{Math.round(confidence * 100)}%</b></div><input type="range" min=".05" max=".99" step=".01" value={confidence} onChange={e => setConfidence(+e.target.value)} className="mt-3 w-full" /></div><div className="rounded-xl border border-border bg-surface-2 p-3"><div className="flex justify-between text-[10px] uppercase tracking-[.14em] text-faint"><span>Detection frequency</span><b className="text-text">Every {freq} frames</b></div><input type="range" min="1" max="12" value={freq} onChange={e => setFreq(+e.target.value)} className="mt-3 w-full" /></div><button onClick={authorizeAndStart} className="rounded-xl bg-accent px-5 text-xs font-semibold text-bg"><SlidersHorizontal className="mr-2 inline h-4 w-4" /> Apply & dispatch</button></div>
      {error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">{error}</div>}{status.last_error && <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">Gateway: {status.last_error}</div>}
    </section>

    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">{[["State", status.running ? "ACTIVE" : "IDLE", Activity], ["FPS", status.fps.toFixed(1), Gauge], ["Inference", `${status.inference_ms.toFixed(0)} ms`, Gauge], ["Findings", String(status.findings), Siren], ["Evidence", String(status.evidence), FileText]].map(([a, b, I]) => { const Icon = I as typeof Activity; return <div key={String(a)} className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><Icon className="float-right h-4 w-4 text-accent" /><div className="text-[10px] uppercase tracking-[.14em] text-faint">{a}</div><div className="mt-2 text-2xl font-semibold text-text">{b}</div><div className="mt-1 text-xs text-muted">live gateway telemetry</div></div>; })}</section>

    <section className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Capability ON / OFF</div><div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3"><b className="text-sm text-text">{selectedTender?.category || "No tender selected"}</b><div className="mt-1 text-xs text-muted">{selectedReq?.label || "Select an inspection requirement"}</div></div><div className="mt-4 space-y-1">{CAPS.map(([label, key]) => <div key={key} className="flex items-center justify-between py-2"><span className={`text-xs ${selected[key] ? "text-text" : "text-muted"}`}>{label}</span><Toggle checked={!!selected[key]} onChange={v => setSelected(s => ({ ...s, [key]: v }))} /></div>)}</div><div className="mt-4 rounded-xl border border-border bg-surface-2 p-3 text-xs leading-5 text-muted"><b className="text-text">Evidence policy</b><br />Visual rover evidence is observational. Specialist material, thickness, strength and electrical certification are not inferred from RGB vision.</div></aside>

      <div ref={viewer} className={`min-w-0 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm ${full ? "bg-black p-3" : ""}`}><div className="flex items-center justify-between border-b border-border px-4 py-3"><div className="flex gap-1 rounded-lg bg-surface-2 p-1">{(["live", "evidence", "contract"] as const).map(x => <button key={x} onClick={() => setTab(x)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize ${tab === x ? "bg-surface text-text" : "text-muted"}`}>{x}</button>)}</div><button onClick={() => document.fullscreenElement ? document.exitFullscreen() : viewer.current?.requestFullscreen()} className="rounded-lg border border-border px-3 py-1.5 text-xs text-text">{full ? <Minimize2 className="inline h-3.5 w-3.5" /> : <Maximize2 className="inline h-3.5 w-3.5" />} Fullscreen</button></div>
        {tab === "live" && <div className="p-3"><div className={`relative overflow-hidden rounded-xl bg-[#0b0e13] ${full ? "h-[calc(100vh-58px)]" : "min-h-[55vh] xl:min-h-[68vh]"}`}>{stream ? <img src={stream} alt="SENTRY FIELD annotated live inspection" className="h-full w-full object-contain" onError={() => { setError("Cannot read gateway stream. Check camera URL and local gateway."); void stop(); }} /> : <div className="absolute inset-0 grid place-items-center text-center"><div><Camera className="mx-auto h-10 w-10 text-accent" /><div className="mt-3 font-semibold text-text">Inspection stopped</div><div className="mt-1 text-xs text-muted">Select tender → approve mission → dispatch rover.</div></div></div>}<div className="absolute left-4 top-4 flex flex-wrap gap-2"><Badge tone={active ? "success" : "muted"}>{active ? "LIVE" : "OFFLINE"}</Badge>{status.mission_id && <Badge tone="muted">Mission {status.mission_id}</Badge>}{selectedTender && <Badge tone="muted">{selectedTender.demo_site}</Badge>}</div><div className="absolute bottom-4 left-4 flex gap-2"><Badge tone="muted"><MapPin className="mr-1 inline h-3 w-3" />GPS {status.gps.status}</Badge>{status.last_identity && <Badge tone="success">ID {status.last_identity.slice(0, 45)}</Badge>}</div></div></div>}
        {tab === "evidence" && <div className="divide-y divide-border">{status.recent_events.length ? status.recent_events.slice(0, 25).map((e, i) => <div key={`${e.type}-${i}`} className="grid gap-3 p-4 md:grid-cols-[56px_1fr_auto] md:items-center"><div className="grid aspect-square place-items-center rounded-xl border border-border bg-surface-2"><FileText className="h-5 w-5 text-accent" /></div><div><div className="text-sm font-semibold text-text">{e.type}{e.track_id ? ` · ${e.track_id}` : ""}</div><div className="mt-1 text-xs text-muted">{e.value || `Detector: ${e.detector || "vision"}`}</div><div className="mt-1 text-xs text-faint">Mission {e.mission_id || mission} · Requirement {e.requirement_id || req}</div></div><Badge tone="success">{e.type === "identity" ? "Identity" : "Observed"}</Badge></div>) : <div className="p-10 text-center text-sm text-muted">No evidence captured yet.</div>}</div>}
        {tab === "contract" && <div className="space-y-4 p-4"><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Requirement {req}</div><div className="mt-1 text-lg font-semibold text-text">{selectedReq?.label || selectedTender?.title || "Inspection requirement"}</div><div className="mt-1 text-xs text-muted">{selectedTender?.contract_location || "—"} · Source verified {selectedTender?.source_verified_on || "—"}</div><div className="mt-4 grid gap-3 sm:grid-cols-3"><label className="rounded-xl border border-border bg-surface p-3"><span className="text-[10px] uppercase tracking-[.14em] text-faint">Expected</span><input type="number" min="0" value={expected} onChange={e => setExpected(Math.max(0, +e.target.value || 0))} className="mt-1 h-9 w-full rounded-lg border border-border bg-bg/40 px-2 text-sm text-text" /></label><div className="rounded-xl border border-border bg-surface p-3"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Observed</div><div className="mt-1 text-xl font-semibold text-text">{observed}</div><div className="text-xs text-muted">derived from recent evidence tracks</div></div><div className="rounded-xl border border-border bg-surface p-3"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Discrepancy</div><div className="mt-1 text-xl font-semibold text-text">{discrepancy}</div><div className="text-xs text-muted">expected − observed</div></div></div></div><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[.14em] text-faint">Investigator explanation</div><p className="mt-2 text-sm leading-6 text-text">{discrepancy > 0 ? `Field evidence currently supports ${observed} observed item(s) against ${expected} expected. This is a discrepancy signal, not a fraud finding.` : "No positive quantity discrepancy is currently derived from the visible evidence stream."}</p><div className="mt-3 rounded-lg border border-border bg-surface p-3 text-xs leading-5 text-muted"><b className="text-text">Next verification:</b> reconcile asset identity and field evidence with approved variation, maintenance/outage, work-in-progress and contract records.</div></div></div>}
      </div>

      <aside className="space-y-5"><div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Mission chain</div><div className="mt-3 space-y-2 text-xs">{[["Tender", selectedTender?.tender_id || "—"], ["Requirement", selectedReq?.id || "—"], ["Capability", selectedReq?.capability || "—"], ["Machine", selectedTender?.machine || "—"], ["Inspection", status.running ? "RUNNING" : "READY"], ["Evidence", String(status.evidence)], ["Comparison", discrepancy ? `${discrepancy} discrepancy` : "No positive discrepancy"]].map(([a, b]) => <div key={a} className="flex items-center justify-between rounded-lg border border-border bg-surface-2 px-3 py-2"><span className="text-muted">{a}</span><span className="max-w-[58%] truncate font-semibold text-text">{b}</span></div>)}</div></div><div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-faint">Camera / GPS</div><div className="mt-3"><Field label="Camera URL" value={camera} onChange={setCamera} /><div className="mt-3 grid grid-cols-2 gap-2"><div className="rounded-lg border border-border bg-surface-2 p-3"><div className="text-[10px] text-faint">GPS</div><div className="mt-1 text-sm font-semibold text-text">{status.gps.status}</div></div><div className="rounded-lg border border-border bg-surface-2 p-3"><div className="text-[10px] text-faint">FPS</div><div className="mt-1 text-sm font-semibold text-text">{status.fps.toFixed(1)}</div></div></div></div></div><div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-faint"><Target className="h-3.5 w-3.5" /> Contract source</div><div className="mt-2 text-xs leading-5 text-muted">{selectedTender?.verification_notes || "Choose a tender to load its inspection policy."}</div></div></aside>
    </section>
  </main>;
}
