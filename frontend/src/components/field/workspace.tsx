"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, Camera, CheckCircle2, FileText, Gauge, MapPin, Radar, ShieldCheck, Siren, Wifi, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/page";

const capabilities = ["Pothole", "Road crack", "Streetlight", "CCTV", "Signboard", "Drain / manhole", "Solar panel", "QR / asset ID", "OCR"];
const apiBase = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";
const defaultCamera = process.env.NEXT_PUBLIC_SENTRY_CAMERA_URL?.trim() || "http://10.91.92.137:4747/video";

type FieldStatus = {
  running: boolean;
  camera_url: string;
  fps: number;
  findings: number;
  evidence: number;
  last_detection: { type: string; confidence: number; track_id?: string | null } | null;
  last_error: string | null;
  recent_events: Array<{
    type: string;
    confidence: number;
    track_id?: string | null;
    detector?: string;
  }>;
};

const emptyStatus: FieldStatus = {
  running: false,
  camera_url: defaultCamera,
  fps: 0,
  findings: 0,
  evidence: 0,
  last_detection: null,
  last_error: null,
  recent_events: [],
};

export function FieldWorkspace() {
  const [tab, setTab] = useState<"live" | "evidence" | "contract">("live");
  const [armed, setArmed] = useState(true);
  const [cameraUrl, setCameraUrl] = useState(defaultCamera);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<FieldStatus>(emptyStatus);
  const [gatewayOnline, setGatewayOnline] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);

  const cameraActive = Boolean(streamUrl);

  const startCamera = () => {
    const source = cameraUrl.trim();
    if (!source) return;
    setStreamError(null);
    setStreamUrl(`${apiBase}/stream?camera_url=${encodeURIComponent(source)}&t=${Date.now()}`);
    setArmed(true);
  };

  const stopCamera = () => {
    setStreamUrl(null);
    setStatus((current) => ({ ...current, running: false }));
  };

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const response = await fetch(`${apiBase}/status`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Gateway returned ${response.status}`);
        const payload = (await response.json()) as FieldStatus;
        if (!active) return;
        setStatus(payload);
        setGatewayOnline(true);
      } catch {
        if (!active) return;
        setGatewayOnline(false);
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), 900);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const latestEvidence = useMemo(() => {
    return status.recent_events.slice(0, 8).map((event, index) => ({
      id: event.track_id || `EV-${String(index + 1).padStart(4, "0")}`,
      type: event.type,
      confidence: `${Math.round(event.confidence * 100)}%`,
      detector: event.detector || "vision",
    }));
  }, [status.recent_events]);

  return (
    <main className="space-y-6">
      <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent">
              <Radar className="h-3.5 w-3.5" />
              SENTRY FIELD <span className="text-faint">/</span>
              <span className="text-muted">Physical Verification Console</span>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-text md:text-5xl">Field mission control</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
              Start the field camera from this screen, run the local vision gateway, and keep live AI findings beside the stream.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone={gatewayOnline ? "success" : "muted"}>
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              {gatewayOnline ? "Gateway online" : "Gateway offline"}
            </Badge>
            <Badge tone={cameraActive ? "info" : "muted"}>
              <Wifi className="h-3 w-3" />
              {cameraActive ? "Camera live" : "Camera stopped"}
            </Badge>
            <button
              onClick={() => (cameraActive ? stopCamera() : startCamera())}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-text hover:border-accent/40"
            >
              {cameraActive ? "Stop camera" : "Start camera"}
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto]">
          <label className="block">
            <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">DroidCam source</span>
            <input
              value={cameraUrl}
              onChange={(event) => setCameraUrl(event.target.value)}
              className="h-10 w-full rounded-xl border border-border bg-bg/40 px-3 text-xs text-text outline-none placeholder:text-faint focus:border-accent/50"
              placeholder="http://10.x.x.x:4747/video"
            />
          </label>
          <div className="flex items-end gap-2">
            <button
              onClick={startCamera}
              className="h-10 rounded-xl bg-accent px-4 text-xs font-semibold text-bg hover:bg-accent-hi"
            >
              Start field feed
            </button>
            <button
              onClick={stopCamera}
              disabled={!cameraActive}
              className="h-10 rounded-xl border border-border px-4 text-xs font-semibold text-text disabled:opacity-40"
            >
              Disconnect
            </button>
          </div>
        </div>

        {streamError && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
            <XCircle className="h-3.5 w-3.5" /> {streamError}
          </div>
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Mission coverage", "47 / 50", "94% inspected", Radar],
          ["Field findings", String(status.findings), "Live detections", Siren],
          ["Evidence captured", String(status.evidence), "Recent traceable events", FileText],
          ["Live inference", `${status.fps.toFixed(1)} FPS`, cameraActive ? "Local vision gateway" : "Waiting for camera", Gauge],
        ].map(([a, b, c, Icon]) => (
          <div key={a as string} className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
            <div className="flex justify-between">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{a as string}</div>
                <div className="mt-2 text-2xl font-semibold text-text">{b as string}</div>
                <div className="mt-1 text-xs text-muted">{c as string}</div>
              </div>
              <Icon className="h-4 w-4 text-accent" />
            </div>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[230px_minmax(0,1fr)_300px]">
        <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Mission #ST-2048</div>
          <div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3">
            <div className="text-sm font-semibold text-text">Urban road & asset verification</div>
            <div className="mt-1 text-xs leading-5 text-muted">Verify road defects, streetlights, cameras and asset identity.</div>
          </div>
          <div className="my-4 h-px bg-border" />
          <div className="flex justify-between text-xs"><span className="text-muted">Coverage</span><span className="text-text">94%</span></div>
          <div className="mt-2 h-1.5 rounded-full bg-bg-2"><div className="h-full w-[94%] rounded-full bg-accent" /></div>
          <div className="mt-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Capabilities</div>
          <div className="mt-3 space-y-2">
            {capabilities.map((item) => (
              <div key={item} className="flex items-center gap-2 text-xs text-text"><CheckCircle2 className="h-3.5 w-3.5 text-success" />{item}</div>
            ))}
          </div>
        </aside>

        <div className="min-w-0 rounded-2xl border border-border bg-surface shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
            <div className="flex gap-1 rounded-lg bg-surface-2 p-1">
              {(["live", "evidence", "contract"] as const).map((item) => (
                <button key={item} onClick={() => setTab(item)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize ${tab === item ? "bg-surface text-text shadow-sm" : "text-muted"}`}>
                  {item}
                </button>
              ))}
            </div>
            <button
              onClick={() => setArmed(!armed)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${armed ? "border-success/30 bg-success/10 text-success" : "border-border text-muted"}`}
            >
              {armed ? "Auto-capture armed" : "Auto-capture paused"}
            </button>
          </div>

          {tab === "live" && (
            <div className="p-4">
              <div className="relative aspect-video overflow-hidden rounded-xl bg-[#10131a]">
                {streamUrl ? (
                  <img
                    src={streamUrl}
                    alt="SENTRY FIELD annotated live camera"
                    className="h-full w-full object-contain"
                    onError={() => {
                      setStreamError("Could not read the local field gateway stream. Check the gateway terminal and DroidCam URL.");
                      setGatewayOnline(false);
                      stopCamera();
                    }}
                  />
                ) : (
                  <div className="absolute inset-0 grid place-items-center p-8 text-center">
                    <div>
                      <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-border bg-surface-2 text-accent"><Camera className="h-6 w-6" /></div>
                      <div className="mt-4 text-sm font-semibold text-text">Field camera is stopped</div>
                      <div className="mt-1 text-xs text-muted">Set the DroidCam URL above and press “Start field feed”.</div>
                    </div>
                  </div>
                )}
                <div className="absolute left-4 top-4 flex gap-2">
                  <Badge tone={cameraActive ? "success" : "muted"}><Activity className="h-3 w-3" /> {cameraActive ? "LIVE" : "OFFLINE"}</Badge>
                  <Badge tone="muted"><Camera className="h-3 w-3" /> Front camera</Badge>
                </div>
                <div className="absolute bottom-4 left-4 text-[10px] text-white/70">
                  <MapPin className="mr-1 inline h-3 w-3" /> {cameraActive ? "Local field gateway" : "Waiting for camera"}
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-border bg-surface-2 p-3">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-faint">Current finding</div>
                  <div className="mt-1 text-sm font-semibold text-text">{status.last_detection?.type || "None"}</div>
                  <div className="mt-1 text-xs text-muted">{status.last_detection ? `Confidence ${Math.round(status.last_detection.confidence * 100)}%` : "No accepted detection"}</div>
                </div>
                <div className="rounded-xl border border-border bg-surface-2 p-3">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-faint">Context</div>
                  <div className="mt-1 text-sm font-semibold text-text">Person filtering enabled</div>
                  <div className="mt-1 text-xs text-muted">Specialized + context models</div>
                </div>
                <div className="rounded-xl border border-border bg-surface-2 p-3">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-faint">Evidence</div>
                  <div className="mt-1 text-sm font-semibold text-text">{status.evidence > 0 ? "Events preserved" : "Waiting"}</div>
                  <div className="mt-1 text-xs text-muted">Writer stays on the local gateway</div>
                </div>
              </div>
            </div>
          )}

          {tab === "evidence" && (
            <div className="divide-y divide-border">
              {latestEvidence.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted">No live evidence yet. Start the field feed first.</div>
              ) : (
                latestEvidence.map((item) => (
                  <div key={`${item.id}-${item.type}-${item.confidence}`} className="grid gap-3 p-4 md:grid-cols-[76px_1fr_auto] md:items-center">
                    <div className="flex aspect-square items-center justify-center rounded-xl border border-border bg-surface-2"><FileText className="h-6 w-6 text-accent" /></div>
                    <div>
                      <div className="text-sm font-semibold text-text">{item.type} · {item.id}</div>
                      <div className="mt-1 text-xs text-muted">Detector: {item.detector}</div>
                      <div className="mt-1 text-xs text-faint">Confidence {item.confidence}</div>
                    </div>
                    <Badge tone="success">Observed</Badge>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "contract" && (
            <div className="p-4">
              <div className="rounded-xl border border-border bg-surface-2 p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-faint">Requirement R-01</div>
                <div className="mt-1 text-lg font-semibold text-text">Install and maintain 50 streetlights</div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {[["Expected", "50"], ["Observed", "47"], ["Unverified", "3"]].map(([label, value]) => (
                    <div key={label} className="rounded-xl border border-border bg-surface p-3">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-faint">{label}</div>
                      <div className="mt-1 text-xl font-semibold text-text">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
            <div className="flex justify-between"><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Field signal</div><Badge tone={gatewayOnline && cameraActive ? "success" : "muted"}>{gatewayOnline && cameraActive ? "Stable" : "Waiting"}</Badge></div>
            <div className="mt-4 space-y-3">
              {[["Camera", cameraActive ? "LIVE" : "Stopped"], ["Inference", cameraActive ? `${status.fps.toFixed(1)} FPS` : "Waiting"], ["Evidence writer", status.evidence ? `${status.evidence} events` : "Ready"], ["GPS", "Not connected"]].map(([label, value]) => (
                <div key={label} className="flex justify-between text-xs"><span className="text-text">{label}</span><span className={cameraActive && value !== "Not connected" ? "text-success" : "text-faint"}>{value}</span></div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-accent/20 bg-accent/5 p-4">
            <div className="flex gap-3"><ShieldCheck className="h-5 w-5 text-accent" /><div><div className="text-sm font-semibold text-text">Investigator attention</div><p className="mt-1 text-xs leading-5 text-muted">Observed discrepancies become verification tasks, not automatic legal conclusions.</p></div></div>
          </div>
          {status.last_error && (
            <div className="rounded-2xl border border-danger/30 bg-danger/10 p-4">
              <div className="text-xs font-semibold text-danger">Gateway error</div>
              <div className="mt-1 text-xs leading-5 text-danger/80">{status.last_error}</div>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}
