"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Camera, MapPin, Radar, ShieldCheck } from "lucide-react";

const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";

type FieldTenderLead = {
  tender_id: string;
  reference_number: string;
  source_record_id: string | null;
  tender_title: string;
  subject: string;
  source_url: string | null;
  investigation_type: "tender";
  priority: "review";
  risk_level: "insufficient";
  typology_count: number;
  linked_records: number;
  evidence_strength: "high" | "limited";
  evidence_completeness: number;
  primary_pattern: string;
  reasons: string[];
};

export function FieldTenderQueue() {
  const [items, setItems] = useState<FieldTenderLead[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(BACKEND + "/api/investigations/field-tender-leads", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("field_leads_" + response.status);
        return (await response.json()) as { items: FieldTenderLead[]; total: number };
      })
      .then((payload) => alive && setItems(payload.items))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, []);

  if (items === null && !error) {
    return <div className="grid gap-3 md:grid-cols-2"><Skeleton /><Skeleton /><Skeleton /><Skeleton /></div>;
  }

  if (error) {
    return <div className="rounded-2xl border border-danger/20 bg-danger/5 p-5 text-sm text-muted">Physical verification candidates could not be loaded from the backend.</div>;
  }

  if (!items?.length) {
    return (
      <div className="rounded-2xl border border-border bg-surface p-6 text-sm text-muted">
        No physical-verification tender leads are currently available.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <article key={item.tender_id} className="flex flex-col rounded-2xl border border-border bg-surface p-5 transition hover:border-accent/30">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.13em] text-accent">
              <Radar className="h-3 w-3" /> Physical verification
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-[.12em] text-faint">{item.evidence_strength} evidence</span>
          </div>

          <div className="mt-4">
            <div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Tender</div>
            <h2 className="mt-1 text-[15px] font-semibold leading-6 text-text">{item.tender_title}</h2>
            <div className="mt-1 font-mono text-[10px] text-faint">{item.reference_number}</div>
          </div>

          <div className="mt-4 space-y-2 text-xs">
            <div className="flex items-start gap-2 rounded-lg border border-border bg-bg-2/40 px-3 py-2.5">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
              <span className="text-muted">{item.primary_pattern || "Registered physical verification profile"}</span>
            </div>
            {item.reasons.slice(0, 3).map((reason) => (
              <div key={reason} className="flex items-start gap-2 text-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                {reason}
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap gap-2 text-[10px] text-faint">
            <span className="rounded-md border border-border bg-bg-2 px-2 py-1">{Math.round(item.evidence_completeness * 100)}% evidence completeness</span>
            <span className="rounded-md border border-border bg-bg-2 px-2 py-1">{item.linked_records} linked record</span>
          </div>

          <div className="mt-auto pt-5">
            <Link href={"/field?tender=" + encodeURIComponent(item.tender_id)} className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent">
              Open physical verification <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1.5 text-[10px] text-faint hover:text-text">
              <MapPin className="h-3 w-3" /> Official source
            </a>
          ) : null}

          <div className="mt-3 flex items-center gap-2 text-[10px] text-faint">
            <Camera className="h-3 w-3 text-accent" /> FIELD mission can be launched from the selected tender.
          </div>
        </article>
      ))}
    </div>
  );
}

function Skeleton() {
  return <div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" />;
}
