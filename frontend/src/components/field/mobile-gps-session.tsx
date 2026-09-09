"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2, MapPin, Navigation, ShieldAlert } from "lucide-react";

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";

type GpsState = {
  status: string;
  source: string | null;
  lat: number | null;
  lon: number | null;
  accuracy_m: number | null;
  captured_at: number | null;
  received_at: number | null;
  mission_id: string | null;
  requirement_id: string | null;
  tender_id: string | null;
};

type GatewayStatus = {
  authorized: boolean;
  mission_id: string | null;
  requirement_id: string | null;
  tender_id: string | null;
  machine_id: string | null;
  speed: number | null;
  gps: GpsState;
};

const EMPTY_GPS: GpsState = {
  status: "unavailable",
  source: null,
  lat: null,
  lon: null,
  accuracy_m: null,
  captured_at: null,
  received_at: null,
  mission_id: null,
  requirement_id: null,
  tender_id: null,
};

const EMPTY_STATUS: GatewayStatus = {
  authorized: false,
  mission_id: null,
  requirement_id: null,
  tender_id: null,
  machine_id: null,
  speed: null,
  gps: EMPTY_GPS,
};

export function MobileGpsSession({ tenderKey, requirementId }: { tenderKey: string; requirementId: string }) {
  const [status, setStatus] = useState<GatewayStatus>(EMPTY_STATUS);
  const [watching, setWatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);
  const sessionDeviceId = useRef<string>("");

  const gpsLive = status.gps.status === "live" && status.gps.lat != null && status.gps.lon != null;
  const exactMission = status.authorized && status.tender_id === tenderKey && status.requirement_id === requirementId;

  function clearWatch() {
    if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setWatching(false);
  }

  useEffect(() => {
    sessionDeviceId.current = `mobile-gps:${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    let alive = true;
    const poll = async () => {
      try {
        const response = await fetch(`${API}/status`, { cache: "no-store" });
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as GatewayStatus;
        if (!alive) return;
        setStatus(payload);
        if (!payload.authorized && watchId.current !== null) clearWatch();
        if (
          payload.authorized &&
          (payload.tender_id !== tenderKey || payload.requirement_id !== requirementId)
        ) {
          clearWatch();
          setError("The gateway is authorised for a different tender or requirement.");
        }
      } catch {
        if (alive) setError("Field gateway status is unavailable.");
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 900);
    return () => {
      alive = false;
      window.clearInterval(timer);
      if (watchId.current !== null && "geolocation" in navigator) navigator.geolocation.clearWatch(watchId.current);
      watchId.current = null;
    };
  }, [requirementId, tenderKey]);

  function startGps() {
    if (!("geolocation" in navigator)) {
      setError("This browser does not expose device geolocation.");
      return;
    }
    if (!exactMission || !status.mission_id) {
      setError("Authorise the exact rover mission before enabling mobile GPS.");
      return;
    }
    clearWatch();
    setError(null);
    const missionId = status.mission_id;
    watchId.current = navigator.geolocation.watchPosition(
      async (position) => {
        if (!sessionDeviceId.current) sessionDeviceId.current = `mobile-gps:${Date.now()}`;
        try {
          const response = await fetch(`${API}/telemetry/mobile`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tender_id: tenderKey,
              mission_id: missionId,
              requirement_id: requirementId,
              machine_id: sessionDeviceId.current,
              lat: position.coords.latitude,
              lon: position.coords.longitude,
              accuracy_m: position.coords.accuracy,
              captured_at: position.timestamp,
              speed: position.coords.speed,
            }),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(payload.detail || `GPS telemetry rejected (${response.status})`);
          setStatus((current) => ({ ...current, gps: payload.gps }));
          setError(null);
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : "Could not send mobile GPS telemetry");
        }
      },
      (reason) => {
        setWatching(false);
        setError(reason.message || "Device GPS permission failed");
      },
      { enableHighAccuracy: true, maximumAge: 2500, timeout: 10000 },
    );
    setWatching(true);
  }

  function stopGps() {
    clearWatch();
  }

  const capturedLabel = status.gps.captured_at
    ? new Date(status.gps.captured_at * 1000).toLocaleTimeString()
    : "—";

  return (
    <section className="rounded-2xl border border-accent/20 bg-surface p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-accent"><Navigation className="h-3.5 w-3.5" /> SENTRY FIELD / PHASE 4</div>
          <h2 className="mt-1 text-lg font-semibold text-text">Mobile GPS session</h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">The operator phone supplies real browser geolocation. Each sample is bound server-side to the authorised tender, requirement and mission.</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${gpsLive ? "border-success/30 bg-success/10 text-success" : "border-border text-muted"}`}>
          {gpsLive ? <CheckCircle2 className="h-3 w-3" /> : <MapPin className="h-3 w-3" />}
          {gpsLive ? "GPS live" : "GPS unavailable"}
        </span>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Latitude</div><div className="mt-1 text-sm font-semibold text-text">{gpsLive ? status.gps.lat!.toFixed(6) : "—"}</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Longitude</div><div className="mt-1 text-sm font-semibold text-text">{gpsLive ? status.gps.lon!.toFixed(6) : "—"}</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Accuracy</div><div className="mt-1 text-sm font-semibold text-text">{status.gps.accuracy_m != null ? `±${status.gps.accuracy_m.toFixed(1)} m` : "—"}</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-faint">Captured</div><div className="mt-1 text-sm font-semibold text-text">{capturedLabel}</div></div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="button" onClick={watching ? stopGps : startGps} disabled={!exactMission} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-40">
          {watching ? "Stop mobile GPS" : "Start mobile GPS"}
        </button>
        <span className="text-[11px] text-muted">Source: {status.gps.source || "waiting for device"}</span>
      </div>

      {!status.authorized && <div className="mt-3 flex items-start gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-xs text-muted"><ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />Authorise this exact rover mission first. Mobile GPS cannot publish telemetry before mission authorization.</div>}
      {error && <div className="mt-3 rounded-xl border border-danger/25 bg-danger/10 px-3 py-2.5 text-xs text-danger">{error}</div>}
      {watching && !gpsLive && <div className="mt-3 flex items-center gap-2 text-xs text-muted"><Loader2 className="h-3.5 w-3.5 animate-spin" />Waiting for the phone's first geolocation fix…</div>}
    </section>
  );
}
