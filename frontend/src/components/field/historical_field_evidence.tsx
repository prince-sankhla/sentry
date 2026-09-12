"use client";

import { useEffect, useMemo, useState } from "react";
import { History, MapPin, ShieldCheck } from "lucide-react";

const FIELD_API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";

const LABELS: Record<string, string> = {
  pothole: "Pothole",
  road_crack: "Road crack",
  streetlight: "Streetlight",
  cctv_camera: "CCTV",
  signboard: "Signboard",
  drain: "Drain / manhole",
  solar_panel: "Solar panel",
  road_barrier: "Road barrier",
  manhole_cover: "Manhole cover",
  asset_qr: "QR / asset ID",
  asset_text: "OCR / asset text",
  asset_barcode: "Barcode",
};

type Observation = {
  capability?: string;
  observation?: string;
  confidence?: number | null;
  track_id?: string | null;
  frame_url?: string | null;
  gps?: { lat?: number | null; lon?: number | null } | null;
  observed_at?: number | null;
};

type Verification = {
  id: string;
  version: number;
  status: string;
  mission_id: string;
  submitted_at?: string | null;
  evidence_count: number;
  gps_evidence_count: number;
  observations?: Observation[];
};

type VerificationStatus = {
  verified: boolean;
  latest: Verification | null;
  history: Verification[];
};

function labelFor(capability?: string) {
  return LABELS[capability || ""] || (capability ? capability.replaceAll("_", " ") : "Field evidence");
}

function frameUrl(value?: string | null) {
  if (!value) return null;
  return value.startsWith("http") ? value : `${FIELD_API}${value}`;
}

function formatDate(value?: string | null) {
  if (!value) return "Unknown time";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function HistoricalFieldEvidence({ tenderKey }: { tenderKey?: string }) {
  const [verification, setVerification] = useState<VerificationStatus | null>(null);

  useEffect(() => {
    if (!tenderKey) return;
    let alive = true;
    fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000"}/api/investigations/tenders/${encodeURIComponent(tenderKey)}/field-verification-status`, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error())))
      .then((payload) => {
        if (alive) setVerification(payload as VerificationStatus);
      })
      .catch(() => {
        if (alive) setVerification(null);
      });
    return () => {
      alive = false;
    };
  }, [tenderKey]);

  const versions = useMemo(
    () => (verification?.history || []).slice().sort((a, b) => b.version - a.version),
    [verification],
  );

  const evidenceTotal = useMemo(
    () => versions.reduce((total, version) => total + (version.observations || []).filter((item) => item.frame_url).length, 0),
    [versions],
  );

  if (!tenderKey || !versions.length) return null;

  return (
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent">
            <History className="h-3.5 w-3.5" /> Historical FIELD evidence
          </div>
          <h2 className="mt-2 text-lg font-semibold text-text">Previous verified field captures</h2>
          <p className="mt-1 text-sm text-muted">Earlier verification versions remain available here, including their original evidence frames and GPS context.</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border bg-bg/20 px-3 py-2 text-xs text-muted">
          <ShieldCheck className="h-4 w-4 text-accent" />
          {versions.length} version{versions.length === 1 ? "" : "s"} · {evidenceTotal} evidence frames
        </div>
      </div>

      <div className="mt-5 space-y-5">
        {versions.map((version) => {
          const observations = (version.observations || []).filter((item) => item.frame_url);
          if (!observations.length) return null;
          return (
            <div key={version.id} className="rounded-xl border border-border bg-bg/10 p-4">
              <div className="flex flex-col gap-1.5 border-b border-border pb-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-text">Version {version.version}</span>
                    <span className="rounded-full border border-accent/20 bg-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[.12em] text-accent">{version.status}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted">{formatDate(version.submitted_at)} · Mission {version.mission_id}</div>
                </div>
                <div className="text-xs text-muted">{observations.length} saved frame{observations.length === 1 ? "" : "s"} · {version.gps_evidence_count} GPS</div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {observations.map((item, index) => {
                  const src = frameUrl(item.frame_url);
                  return (
                    <article key={`${version.id}:${item.track_id || "frame"}:${index}`} className="overflow-hidden rounded-xl border border-border bg-surface">
                      {src ? (
                        <a href={src} target="_blank" rel="noreferrer" className="block">
                          <img src={src} alt={`${labelFor(item.capability)} evidence`} className="aspect-video w-full object-cover" loading="lazy" />
                        </a>
                      ) : null}
                      <div className="p-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="text-sm font-semibold text-text">{labelFor(item.capability)}</div>
                          {typeof item.confidence === "number" ? <div className="text-xs font-semibold text-accent">{Math.round(item.confidence * 100)}%</div> : null}
                        </div>
                        <div className="mt-1 text-xs text-muted">{item.observation || "Detected field evidence"}</div>
                        {item.gps?.lat != null && item.gps?.lon != null ? (
                          <div className="mt-2 flex items-center gap-1 text-[11px] text-muted">
                            <MapPin className="h-3 w-3" /> {item.gps.lat.toFixed(6)}, {item.gps.lon.toFixed(6)}
                          </div>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
