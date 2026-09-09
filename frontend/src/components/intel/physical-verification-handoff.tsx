"use client";

import { useEffect, useState } from "react";
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

export function PhysicalVerificationHandoff({ initialQuery }: { initialQuery: string }) {
  const [plan, setPlan] = useState<VerificationPlan | null>(null);
  const [notApplicable, setNotApplicable] = useState(false);

  useEffect(() => {
    const reference = initialQuery.trim();
    if (!reference) return;
    let alive = true;
    fetch(`${BACKEND_URL}/api/investigations/field-verification?reference_number=${encodeURIComponent(reference)}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (response.status === 404 || response.status === 409) {
          setNotApplicable(true);
          return null;
        }
        if (!response.ok) throw new Error(`Field verification planning failed: ${response.status}`);
        return (await response.json()) as VerificationPlan;
      })
      .then((payload) => {
        if (alive && payload) setPlan(payload);
      })
      .catch(() => {
        if (alive) setNotApplicable(true);
      });
    return () => { alive = false; };
  }, [initialQuery]);

  if (!plan || notApplicable) return null;

  const firstRequirement = plan.requirements[0];
  const fieldUrl = `/field?tender=${encodeURIComponent(plan.field_tender_key)}&requirement=${encodeURIComponent(firstRequirement.id)}`;

  return (
    <section className="mt-8 overflow-hidden rounded-2xl border border-accent/25 bg-accent/[0.045] shadow-sm">
      <div className="border-b border-accent/15 px-5 py-4 md:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent">
              <Radar className="h-3.5 w-3.5" /> SENTRY FIELD / NEXT VERIFICATION
            </div>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-text">Physical verification required</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
              The procurement record has a registered inspection profile. SENTRY can now hand the exact tender and executable requirement to the field console.
            </p>
          </div>
          <a
            href={fieldUrl}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-bg transition hover:bg-accent-hi"
          >
            Launch SENTRY FIELD <ArrowRight className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4 md:px-6">
        <div className="rounded-xl border border-border bg-surface p-3.5">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><ShieldCheck className="h-3.5 w-3.5 text-success" /> Exact tender</div>
          <div className="mt-2 text-sm font-semibold text-text">{plan.tender.reference_number}</div>
          <div className="mt-1 text-xs text-muted">DB record: {plan.tender.id}</div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-3.5">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><Radar className="h-3.5 w-3.5 text-accent" /> Machine</div>
          <div className="mt-2 text-sm font-semibold text-text">{plan.machine}</div>
          <div className="mt-1 text-xs text-muted">Profile: {plan.profile_id}</div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-3.5">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><MapPin className="h-3.5 w-3.5 text-accent" /> Field site</div>
          <div className="mt-2 text-sm font-semibold text-text">{plan.demo_site || "Site supplied by operator"}</div>
          <div className="mt-1 text-xs text-muted">{plan.category || "Physical procurement asset verification"}</div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-3.5">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><Camera className="h-3.5 w-3.5 text-accent" /> First requirement</div>
          <div className="mt-2 text-sm font-semibold text-text">{firstRequirement.label}</div>
          <div className="mt-1 text-xs text-muted">{firstRequirement.capability} · expected {firstRequirement.expected_quantity}</div>
        </div>
      </div>

      <div className="border-t border-accent/15 px-5 py-4 md:px-6">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Executable verification requirements</div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {plan.requirements.map((requirement) => (
            <a
              key={requirement.id}
              href={`/field?tender=${encodeURIComponent(plan.field_tender_key)}&requirement=${encodeURIComponent(requirement.id)}`}
              className="rounded-xl border border-border bg-surface px-3.5 py-3 transition hover:border-accent/30 hover:bg-surface-2"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-[12px] font-semibold text-text">{requirement.label}</span>
                <span className="font-mono text-[10px] text-faint">{requirement.id}</span>
              </div>
              <div className="mt-1 text-xs text-muted">{requirement.capability} · expected quantity {requirement.expected_quantity}</div>
            </a>
          ))}
        </div>
        {plan.verification_notes && <p className="mt-3 text-[11px] leading-5 text-muted">Verification boundary: {plan.verification_notes}</p>}
      </div>
    </section>
  );
}
