"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Camera, MapPin, Radar, ShieldCheck } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

type Requirement = {
  id: string;
  capability: string;
  label: string;
  expected_quantity: number;
};

type VerificationPlan = {
  tender: {
    id: string;
    reference_number: string;
    title: string;
    source_record_id: string;
    source_url: string | null;
    procuring_entity: string | null;
  };
  verification_required: boolean;
  profile_id: string;
  field_tender_key: string;
  machine: string;
  demo_site: string | null;
  category: string | null;
  requirements: Requirement[];
  verification_notes: string | null;
  source_profile_verified_on: string | null;
};

const CAPABILITY_LABELS: Record<string, string> = {
  pothole: "Pothole",
  road_crack: "Road crack",
  streetlight: "Streetlight",
  cctv_camera: "CCTV",
  signboard: "Signboard",
  drain: "Drain / manhole",
  solar_panel: "Solar panel",
  asset_qr: "QR / asset ID",
  asset_text: "OCR / asset text",
};

export function PhysicalVerificationHandoff({ initialQuery }: { initialQuery: string }) {
  const [plan, setPlan] = useState<VerificationPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [notApplicable, setNotApplicable] = useState(false);

  useEffect(() => {
    const reference = initialQuery.trim();
    if (!reference) {
      setLoading(false);
      setNotApplicable(true);
      return;
    }
    let alive = true;
    setLoading(true);
    setNotApplicable(false);
    fetch(`${BACKEND_URL}/api/investigations/field-verification?reference_number=${encodeURIComponent(reference)}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (response.status === 404 || response.status === 409) return null;
        if (!response.ok) throw new Error(`Field verification planning failed: ${response.status}`);
        return (await response.json()) as VerificationPlan;
      })
      .then((payload) => {
        if (!alive) return;
        setPlan(payload);
        setNotApplicable(!payload);
        setLoading(false);
      })
      .catch(() => {
        if (alive) {
          setPlan(null);
          setNotApplicable(true);
          setLoading(false);
        }
      });
    return () => { alive = false; };
  }, [initialQuery]);

  const capabilities = useMemo(() => {
    const values: string[] = [];
    for (const requirement of plan?.requirements ?? []) {
      if (requirement.capability && !values.includes(requirement.capability)) values.push(requirement.capability);
    }
    return values;
  }, [plan]);

  if (notApplicable) return null;
  if (loading || !plan || !plan.requirements.length) {
    return (
      <section className="mt-8 overflow-hidden rounded-2xl border border-accent/20 bg-accent/[0.035] shadow-sm">
        <div className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between md:px-6">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / VERIFICATION GATE</div>
            <div className="mt-1 text-sm font-semibold text-text">Resolving physical-verification profile…</div>
          </div>
          <span className="text-[11px] text-muted">SENTRY will auto-select capabilities from the tender requirements.</span>
        </div>
      </section>
    );
  }

  const firstRequirement = plan.requirements[0];
  const fieldUrl = `/field?tender=${encodeURIComponent(plan.field_tender_key)}&requirement=${encodeURIComponent(firstRequirement.id)}`;

  return (
    <section className="mt-8 overflow-hidden rounded-2xl border border-accent/25 bg-accent/[0.045] shadow-sm">
      <div className="border-b border-accent/15 px-5 py-4 md:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / NEXT VERIFICATION</div>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-text">Physical verification available</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">This investigation has a registered field profile. SENTRY will carry the exact tender into FIELD and automatically select every executable vision capability.</p>
          </div>
          <a href={fieldUrl} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg transition hover:bg-accent-hi">Launch SENTRY FIELD <ArrowRight className="h-3.5 w-3.5" /></a>
        </div>
        <div className="mt-4 rounded-xl border border-accent/15 bg-accent/5 p-3.5">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent"><Radar className="h-3.5 w-3.5" /> Auto-selected capabilities</div>
          <div className="mt-2 flex flex-wrap gap-2">{capabilities.map((capability) => <span key={capability} className="rounded-full border border-accent/20 bg-accent/10 px-2.5 py-1 text-[10px] font-semibold text-text">{CAPABILITY_LABELS[capability] || capability}</span>)}</div>
          <div className="mt-1.5 text-[11px] text-muted">No manual detector selection is required.</div>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4 md:px-6">
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><ShieldCheck className="h-3.5 w-3.5 text-success" /> Exact tender</div><div className="mt-2 text-sm font-semibold text-text">{plan.tender.reference_number}</div><div className="mt-1 text-xs text-muted">DB record: {plan.tender.id}</div></div>
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><Radar className="h-3.5 w-3.5 text-accent" /> Machine</div><div className="mt-2 text-sm font-semibold text-text">{plan.machine}</div><div className="mt-1 text-xs text-muted">Profile: {plan.profile_id}</div></div>
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><MapPin className="h-3.5 w-3.5 text-accent" /> Field site</div><div className="mt-2 text-sm font-semibold text-text">{plan.demo_site || "Site supplied by operator"}</div><div className="mt-1 text-xs text-muted">{plan.category || "Physical procurement asset verification"}</div></div>
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><Camera className="h-3.5 w-3.5 text-accent" /> Requirements</div><div className="mt-2 text-sm font-semibold text-text">{plan.requirements.length} executable</div><div className="mt-1 text-xs text-muted">All capabilities are derived automatically.</div></div>
      </div>

      <div className="border-t border-accent/15 px-5 py-4 md:px-6">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Executable verification requirements</div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {plan.requirements.map((requirement) => <a key={requirement.id} href={`/field?tender=${encodeURIComponent(plan.field_tender_key)}&requirement=${encodeURIComponent(requirement.id)}`} className="rounded-xl border border-border bg-surface px-3.5 py-3 transition hover:border-accent/30 hover:bg-surface-2"><div className="flex items-center justify-between gap-3"><span className="text-[12px] font-semibold text-text">{requirement.label}</span><span className="font-mono text-[10px] text-faint">{requirement.id}</span></div><div className="mt-1 text-xs text-muted">{CAPABILITY_LABELS[requirement.capability] || requirement.capability} · expected quantity {requirement.expected_quantity}</div></a>)}
        </div>
        {plan.verification_notes && <p className="mt-3 text-[11px] leading-5 text-muted">Verification boundary: {plan.verification_notes}</p>}
      </div>
    </section>
  );
}
