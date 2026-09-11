"use client";

import { ArrowRight, Camera, MapPin, Radar, Siren } from "lucide-react";
import { useRouter } from "next/navigation";

export type TenderRecommendation = {
  tender_id?: string | null;
  reference_number?: string | null;
  title: string;
  procuring_entity?: string | null;
  category?: string | null;
  source_name?: string | null;
  estimated_value?: number | null;
  field_ready?: boolean;
  field_profile_id?: string | null;
  machine?: string | null;
  demo_site?: string | null;
  auto_capabilities?: string[];
  requirements?: { id: string; capability: string; label: string; expected_quantity: number }[];
  pothole_relevant?: boolean;
  reasons?: string[];
};

const CAPABILITY_LABELS: Record<string, string> = {
  pothole: "Pothole", road_crack: "Road crack", streetlight: "Streetlight", cctv_camera: "CCTV",
  signboard: "Signboard", drain: "Drain / manhole", solar_panel: "Solar panel", asset_qr: "QR / asset ID", asset_text: "OCR / asset text",
};

export function PhysicalTenderRecommendations({ fieldReady, pothole }: { fieldReady: TenderRecommendation[]; pothole: TenderRecommendation[] }) {
  const router = useRouter();
  const open = (item: TenderRecommendation) => {
    const target = item.reference_number?.trim() || item.tender_id?.trim();
    if (!target) return;
    const fieldProfile = item.field_ready && item.field_profile_id ? `&fieldProfile=${encodeURIComponent(item.field_profile_id)}` : "";
    router.push(`/investigate?q=${encodeURIComponent(`TENDER:${target}`)}${fieldProfile}`);
  };

  const potholeById = new Map(pothole.map((item) => [item.tender_id || item.reference_number || item.title, item]));
  const unifiedMap = new Map<string, TenderRecommendation>();

  for (const item of fieldReady) {
    const key = item.tender_id || item.reference_number || item.title;
    const potholeMatch = potholeById.get(key);
    unifiedMap.set(key, {
      ...item,
      pothole_relevant: Boolean(item.pothole_relevant || potholeMatch?.pothole_relevant),
      auto_capabilities: item.auto_capabilities?.length ? item.auto_capabilities : potholeMatch?.auto_capabilities,
      field_ready: true,
    });
  }

  for (const item of pothole) {
    const key = item.tender_id || item.reference_number || item.title;
    if (unifiedMap.has(key)) continue;
    unifiedMap.set(key, {
      ...item,
      field_ready: true,
      pothole_relevant: true,
      auto_capabilities: item.auto_capabilities?.length ? item.auto_capabilities : ["pothole", "asset_text"],
      machine: item.machine || "Normal Vision Rover",
    });
  }

  const potholeQueue = [...unifiedMap.values()].filter((item) => item.pothole_relevant).slice(0, 10);

  const renderCards = (items: TenderRecommendation[], emptyLabel: string) => {
    if (items.length === 0) return <div className="mt-4 rounded-xl border border-border bg-bg/20 p-4 text-sm text-muted">{emptyLabel}</div>;
    return (
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {items.map((item) => {
          const target = item.reference_number?.trim() || item.tender_id?.trim() || "";
          const capabilities = item.auto_capabilities ?? [];
          return (
            <button key={`${item.tender_id ?? ""}-${item.reference_number ?? item.title}`} type="button" disabled={!target} onClick={() => open(item)} className="group text-left rounded-2xl border border-border bg-bg/20 p-5 transition hover:border-accent/40 disabled:opacity-50">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[.13em] text-faint">
                    <span className="rounded-full bg-accent/10 px-2 py-1 text-accent">Physical verification</span>
                    <span className="rounded-full bg-surface-2 px-2 py-1 text-text">Pothole / road distress</span>
                  </div>
                  <div className="mt-3 line-clamp-2 text-sm font-semibold leading-5 text-text">{item.title}</div>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                    {item.reference_number ? <span className="font-mono">{item.reference_number}</span> : null}
                    {item.procuring_entity ? <span>{item.procuring_entity}</span> : null}
                    {item.category ? <span>{item.category}</span> : null}
                  </div>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-accent transition-transform group-hover:translate-x-0.5" />
              </div>
              {capabilities.length > 0 ? (
                <div className="mt-4 rounded-xl border border-accent/15 bg-accent/5 p-3">
                  <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.13em] text-accent"><Radar className="h-3.5 w-3.5" /> Auto-selected capabilities</div>
                  <div className="mt-2 flex flex-wrap gap-1.5">{capabilities.map((capability) => <span key={capability} className="rounded-full border border-accent/20 bg-accent/10 px-2 py-1 text-[10px] font-semibold text-text">{CAPABILITY_LABELS[capability] || capability}</span>)}</div>
                  <div className="mt-1.5 text-[10px] text-muted">SENTRY derives these from the tender record. No manual detector choice.</div>
                </div>
              ) : null}
              {item.reasons?.length ? <div className="mt-4 space-y-1 text-[11px] leading-5 text-muted">{item.reasons.slice(0, 2).map((reason) => <div key={reason}>• {reason}</div>)}</div> : null}
              <div className="mt-4 flex flex-wrap items-center gap-3 text-[11px] text-faint">
                <span className="inline-flex items-center gap-1"><Camera className="h-3.5 w-3.5" /> field-capable</span>
                <span className="inline-flex items-center gap-1"><Siren className="h-3.5 w-3.5" /> road inspection</span>
                <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" /> exact tender</span>
                {item.machine ? <span>{item.machine}</span> : null}
                <span className="ml-auto text-accent">Open investigation →</span>
              </div>
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <section className="mt-8 rounded-3xl border border-accent/20 bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-accent"><Camera className="h-3.5 w-3.5" /> SENTRY FIELD / PHYSICAL VERIFICATION</div>
          <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-text">Pothole / road-distress verification queue</h2>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-muted">Real procurement records matching pothole, pot-hole, road-surface distress or patch-repair work. Every card opens the exact tender investigation and then hands off into SENTRY FIELD with automatic inspection capabilities.</p>
        </div>
        <span className="shrink-0 text-[11px] text-faint">{potholeQueue.length} pothole tenders</span>
      </div>
      {renderCards(potholeQueue, "No pothole / road-distress tender records are currently available.")}
    </section>
  );
}
