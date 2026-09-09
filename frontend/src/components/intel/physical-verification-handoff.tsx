"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Camera, MapPin, Radar, ShieldCheck } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";
const FIELD_API_URL = process.env.NEXT_PUBLIC_FIELD_API_URL?.trim() || "http://127.0.0.1:8001";

const CAPABILITY_LABELS: Record<string, string> = {
  pothole: "Pothole", road_crack: "Road crack", streetlight: "Streetlight", cctv_camera: "CCTV",
  signboard: "Signboard", drain: "Drain / manhole", solar_panel: "Solar panel", asset_qr: "QR / asset ID", asset_text: "OCR / asset text",
};

type Requirement = { id: string; capability: string; label: string; expected_quantity: number };
type VerificationPlan = {
  tender: { id: string; reference_number: string; title: string; source_record_id: string; source_url: string | null; procuring_entity: string | null };
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
type FieldProfile = {
  id: string;
  tender_id: string;
  reference_number: string;
  title: string;
  source_name: string;
  source_url: string;
  source_verified_on?: string;
  contract_location: string;
  category: string;
  machine: string;
  demo_site: string;
  requirements: Requirement[];
  verification_notes: string;
};

const CASE_PROFILES: Record<string, string> = {
  "AUDIT:2026_CAG_DELHI_CWG_STREETLIGHT": "FIELD-AUDIT-DELHI-CWG",
  "AUDIT:2026_CAG_DHANBAD_LED": "FIELD-AUDIT-DHANBAD-LED",
};

function planFromProfile(profile: FieldProfile): VerificationPlan {
  return {
    tender: {
      id: profile.tender_id,
      reference_number: profile.reference_number,
      title: profile.title,
      source_record_id: profile.tender_id,
      source_url: profile.source_url,
      procuring_entity: profile.source_name,
    },
    verification_required: true,
    profile_id: profile.id,
    field_tender_key: profile.id,
    machine: profile.machine || "Normal Vision Rover",
    demo_site: profile.demo_site || null,
    category: profile.category || null,
    requirements: profile.requirements || [],
    verification_notes: profile.verification_notes || null,
    source_profile_verified_on: profile.source_verified_on || null,
  };
}

export function PhysicalVerificationHandoff({ initialQuery }: { initialQuery: string }) {
  const [plan, setPlan] = useState<VerificationPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const profileId = useMemo(() => CASE_PROFILES[initialQuery.trim()] || "", [initialQuery]);

  useEffect(() => {
    const reference = initialQuery.trim();
    let alive = true;
    setLoading(true);
    setFailed(false);
    setPlan(null);

    const load = async () => {
      try {
        if (profileId) {
          const response = await fetch(`${FIELD_API_URL}/tenders/${encodeURIComponent(profileId)}`, { cache: "no-store" });
          if (!response.ok) throw new Error();
          const profile = (await response.json()) as FieldProfile;
          if (!alive) return;
          setPlan(planFromProfile(profile));
          setLoading(false);
          return;
        }
        if (!reference) throw new Error();
        const response = await fetch(`${BACKEND_URL}/api/investigations/field-verification?reference_number=${encodeURIComponent(reference)}`, { cache: "no-store", headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as VerificationPlan;
        if (!alive) return;
        setPlan(payload);
        setLoading(false);
      } catch {
        if (!alive) return;
        setFailed(true);
        setLoading(false);
      }
    };
    void load();
    return () => { alive = false; };
  }, [initialQuery, profileId]);

  const capabilities = useMemo(() => {
    const seen = new Set<string>();
    return (plan?.requirements ?? []).map((item) => item.capability).filter((value) => { if (!value || seen.has(value)) return false; seen.add(value); return true; });
  }, [plan]);

  if (failed) return null;
  if (loading || !plan || !plan.requirements.length) {
    return (
      <section className="mt-3 overflow-hidden rounded-2xl border border-accent/20 bg-accent/[0.035] shadow-sm">
        <div className="px-5 py-4 md:px-6">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent"><Radar className="h-3.5 w-3.5 animate-pulse" /> SENTRY FIELD / VERIFICATION GATE</div>
          <div className="mt-1 text-sm font-semibold text-text">Resolving physical-verification profile…</div>
          <div className="mt-1 text-[11px] text-muted">SENTRY will auto-select capabilities from the tender requirements.</div>
        </div>
      </section>
    );
  }

  const firstRequirement = plan.requirements[0];
  const fieldUrl = `/field?tender=${encodeURIComponent(plan.field_tender_key)}&requirement=${encodeURIComponent(firstRequirement.id)}`;

  return (
    <section className="mt-3 overflow-hidden rounded-2xl border border-accent/25 bg-accent/[0.045] shadow-sm">
      <div className="border-b border-accent/15 px-5 py-4 md:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-accent"><Radar className="h-3.5 w-3.5" /> SENTRY FIELD / NEXT VERIFICATION</div>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-text">Physical verification available</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">This investigation has a registered field profile. SENTRY carries the exact tender into FIELD and automatically selects every executable vision capability.</p>
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
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><ShieldCheck className="h-3.5 w-3.5 text-success" /> Exact tender</div><div className="mt-2 text-sm font-semibold text-text">{plan.tender.reference_number}</div><div className="mt-1 text-xs text-muted">DB/profile: {plan.profile_id}</div></div>
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><Radar className="h-3.5 w-3.5 text-accent" /> Machine</div><div className="mt-2 text-sm font-semibold text-text">{plan.machine}</div><div className="mt-1 text-xs text-muted">{capabilities.length} auto-selected capabilities</div></div>
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><MapPin className="h-3.5 w-3.5 text-accent" /> Field site</div><div className="mt-2 text-sm font-semibold text-text">{plan.demo_site || "Site supplied by operator"}</div><div className="mt-1 text-xs text-muted">{plan.category || "Physical procurement asset verification"}</div></div>
        <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><Camera className="h-3.5 w-3.5 text-accent" /> Requirements</div><div className="mt-2 text-sm font-semibold text-text">{plan.requirements.length} executable</div><div className="mt-1 text-xs text-muted">All capabilities derived automatically</div></div>
      </div>
    </section>
  );
}
