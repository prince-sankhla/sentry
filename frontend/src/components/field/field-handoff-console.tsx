"use client";

import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Loader2, MapPin, Radar, ShieldCheck, Wifi, XCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type FieldTender = {
  id: string;
  tender_id: string;
  reference_number: string;
  title: string;
  source_name: string;
  contract_location: string;
  category: string;
  machine: string;
  demo_site: string;
  requirements: Requirement[];
  verification_notes: string;
};

export function FieldHandoffConsole({ tenderKey, requirementId }: { tenderKey: string; requirementId: string }) {
  const [tender, setTender] = useState<FieldTender | null>(null);
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [online, setOnline] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatched, setDispatched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      fetch(`${API}/health`, { cache: "no-store" }),
      fetch(`${API}/tenders/${encodeURIComponent(tenderKey)}`, { cache: "no-store" }),
    ])
      .then(async ([healthResponse, tenderResponse]) => {
        if (!tenderResponse.ok) throw new Error("Selected field tender is unavailable");
        const payload = (await tenderResponse.json()) as FieldTender;
        if (!alive) return;
        setOnline(healthResponse.ok);
        setTender(payload);
        const selected = payload.requirements.find((item) => item.id === requirementId) ?? payload.requirements[0] ?? null;
        setRequirement(selected);
      })
      .catch((reason) => alive && setError(reason instanceof Error ? reason.message : "Field handoff unavailable"));
    return () => { alive = false; };
  }, [requirementId, tenderKey]);

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

  if (error && !tender) {
    return (
      <section className="rounded-2xl border border-danger/25 bg-danger/5 p-5 shadow-sm md:p-6">
        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-danger"><XCircle className="h-3.5 w-3.5" /> Field handoff unavailable</div>
        <div className="mt-2 text-sm font-semibold text-text">{error}</div>
        <div className="mt-1 text-xs text-muted">The investigation remains intact; retry the SENTRY FIELD gateway when it is available.</div>
      </section>
    );
  }

  if (!tender || !requirement) return <section className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center gap-2 text-sm text-muted"><Loader2 className="h-4 w-4 animate-spin" /> Resolving exact field requirement…</div></section>;

  return (
    <section className="overflow-hidden rounded-2xl border border-accent/25 bg-surface shadow-sm">
      <div className="border-b border-border bg-accent/[0.045] px-5 py-5 md:px-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / EXACT HANDOFF</div>
            <h1 className="mt-1.5 text-2xl font-semibold tracking-tight text-text">Rover mission ready</h1>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">Investigation context is locked to the selected procurement record and inspection requirement. No tender or requirement is selected by title or free text here.</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${online ? "border-success/30 bg-success/10 text-success" : "border-border bg-surface text-muted"}`}><Wifi className="h-3 w-3" /> {online ? "Gateway online" : "Gateway offline"}</span>
            <button type="button" onClick={dispatch} disabled={!online || dispatching || dispatched} className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-45">
              {dispatching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : dispatched ? <CheckCircle2 className="h-3.5 w-3.5" /> : null}
              {dispatched ? "Rover dispatched" : "Authorise & dispatch rover"}
              {!dispatched && !dispatching ? <ArrowRight className="h-3.5 w-3.5" /> : null}
            </button>
          </div>
        </div>
        {error && <div className="mt-3 rounded-xl border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-danger">{error}</div>}
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4 md:px-6">
        <div className="rounded-xl border border-border bg-surface-2 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-faint"><ShieldCheck className="h-3.5 w-3.5 text-success" /> Tender</div><div className="mt-2 text-sm font-semibold text-text">{tender.reference_number}</div><div className="mt-1 text-xs text-muted">{tender.tender_id} · {tender.source_name}</div></div>
        <div className="rounded-xl border border-accent/20 bg-accent/5 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-accent"><Radar className="h-3.5 w-3.5" /> Requirement</div><div className="mt-2 text-sm font-semibold text-text">{requirement.label}</div><div className="mt-1 text-xs text-muted">{requirement.id} · {requirement.capability} · expected {requirement.expected_quantity}</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-faint"><Radar className="h-3.5 w-3.5" /> Machine</div><div className="mt-2 text-sm font-semibold text-text">{tender.machine}</div><div className="mt-1 text-xs text-muted">{tender.demo_site}</div></div>
        <div className="rounded-xl border border-border bg-surface-2 p-3.5"><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-faint"><MapPin className="h-3.5 w-3.5" /> Site</div><div className="mt-2 text-sm font-semibold text-text">{tender.contract_location}</div><div className="mt-1 text-xs text-muted">{tender.category}</div></div>
      </div>

      <div className="border-t border-border px-5 py-4 md:px-6">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Verification boundary</div>
        <p className="mt-1 text-xs leading-5 text-muted">{tender.verification_notes}</p>
        {dispatched && <div className="mt-3 rounded-xl border border-success/25 bg-success/10 px-3 py-2.5 text-xs text-success">Dispatch accepted by the field gateway. The selected tender, requirement and machine are now linked to the live mission state.</div>}
      </div>
    </section>
  );
}
