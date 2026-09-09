"use client";

import { ArrowRight, Camera, MapPin, Siren } from "lucide-react";

export type TenderRecommendation = {
  tender_id?: string | null;
  reference_number?: string | null;
  title: string;
  procuring_entity?: string | null;
  category?: string | null;
  source_name?: string | null;
  estimated_value?: number | null;
  field_ready?: boolean;
  pothole_relevant?: boolean;
  reasons?: string[];
};

export function PhysicalTenderRecommendations({
  fieldReady,
  pothole,
  onOpen,
}: {
  fieldReady: TenderRecommendation[];
  pothole: TenderRecommendation[];
  onOpen: (target: string) => void;
}) {
  const section = (title: string, subtitle: string, items: TenderRecommendation[], icon: React.ReactNode) => (
    <section className="mt-8 rounded-3xl border border-border bg-surface p-5 shadow-sm md:p-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-accent">{icon}{title}</div>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>
        </div>
        <span className="text-[11px] text-faint">{items.length} tender{items.length === 1 ? "" : "s"}</span>
      </div>
      {items.length === 0 ? (
        <div className="mt-4 rounded-xl border border-border bg-bg/20 p-4 text-sm text-muted">No matching tender records are currently available.</div>
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {items.map((item) => {
            const target = item.reference_number?.trim() || item.tender_id?.trim() || "";
            return (
              <button key={`${item.tender_id ?? ""}-${item.reference_number ?? item.title}`} type="button" disabled={!target} onClick={() => target && onOpen(target)} className="group text-left rounded-2xl border border-border bg-bg/20 p-5 transition hover:border-accent/40 disabled:opacity-50">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[.13em] text-faint">
                      {item.field_ready ? <span className="rounded-full bg-accent/10 px-2 py-1 text-accent">Physical verification</span> : null}
                      {item.pothole_relevant ? <span className="rounded-full bg-surface-2 px-2 py-1 text-text">Pothole / road distress</span> : null}
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
                {item.reasons?.length ? <div className="mt-4 space-y-1 text-[11px] leading-5 text-muted">{item.reasons.slice(0, 2).map((reason) => <div key={reason}>• {reason}</div>)}</div> : null}
                <div className="mt-4 flex items-center gap-3 text-[11px] text-faint">
                  {item.field_ready ? <span className="inline-flex items-center gap-1"><Camera className="h-3.5 w-3.5" /> field-capable</span> : null}
                  {item.pothole_relevant ? <span className="inline-flex items-center gap-1"><Siren className="h-3.5 w-3.5" /> road inspection</span> : null}
                  <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" /> exact tender</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );

  return (
    <>
      {section("Physical verification recommendations", "Core procurement tenders that have a registered SENTRY FIELD inspection profile. These are surfaced separately from generic entity investigations.", fieldReady, <Camera className="h-3.5 w-3.5" />)}
      {section("Pothole & road-distress tenders", "Tender records whose title, description, category or requirements indicate road-surface or pothole-relevant work. Every card opens the exact tender investigation.", pothole, <Siren className="h-3.5 w-3.5" />)}
    </>
  );
}
