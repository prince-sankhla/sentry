"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, MapPin, ShieldCheck } from "lucide-react";

const STORAGE_KEY = "sentry.field.result";

type Result = {
  status: string;
  mission_id: string;
  tender?: { id: string; reference_number: string; title: string; procuring_entity?: string | null };
  summary?: { expected_total: number; observed_total: number; gap_total: number; evidence_count: number; gps_evidence_count: number; observation_count: number };
  discrepancies?: { requirement_id: string; capability: string; label: string; expected: number; observed: number; gap: number }[];
  possible_explanations?: string[];
  next_checks?: string[];
  guardrail?: string;
};

export function FieldVerificationResult({ reference }: { reference: string }) {
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Result;
      if (parsed.tender?.reference_number === reference || parsed.tender?.id === reference) setResult(parsed);
    } catch {
      // Ignore malformed stale client state.
    }
  }, [reference]);

  if (!result) return null;
  const summary = result.summary;
  const discrepancy = result.status === "discrepancy_review";

  return (
    <section className="mt-4 overflow-hidden rounded-2xl border border-accent/25 bg-accent/[0.045] shadow-sm">
      <div className="border-b border-accent/15 px-5 py-4 md:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.17em] text-accent"><ShieldCheck className="h-3.5 w-3.5" /> FIELD → SENTRY / VERIFICATION RESULT</div>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-text">Physical verification returned to investigation</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">Mission {result.mission_id} has been reconciled against the tender requirements. This is an observation/discrepancy signal for investigator review, not an automatic fraud finding.</p>
          </div>
          <div className={`inline-flex shrink-0 items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${discrepancy ? "bg-warning/10 text-warning" : "bg-success/10 text-success"}`}>
            {discrepancy ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            {discrepancy ? "Discrepancy signal" : "No observed shortfall"}
          </div>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-5 md:px-6">
        <Metric label="Expected" value={summary?.expected_total ?? 0} />
        <Metric label="Observed" value={summary?.observed_total ?? 0} />
        <Metric label="Gap" value={summary?.gap_total ?? 0} />
        <Metric label="Evidence frames" value={summary?.evidence_count ?? 0} />
        <Metric label="GPS-linked" value={summary?.gps_evidence_count ?? 0} icon={<MapPin className="h-3.5 w-3.5" />} />
      </div>

      {result.discrepancies?.length ? (
        <div className="border-t border-accent/15 px-5 py-4 md:px-6">
          <div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Observed discrepancies</div>
          <div className="mt-3 space-y-2">
            {result.discrepancies.map((item) => (
              <div key={item.requirement_id} className="flex flex-col gap-1 rounded-xl border border-border bg-surface px-3.5 py-3 md:flex-row md:items-center md:justify-between">
                <div><div className="text-sm font-semibold text-text">{item.label}</div><div className="text-xs text-muted">{item.capability} · expected {item.expected} · observed {item.observed}</div></div>
                <span className="text-xs font-semibold text-warning">{item.gap} missing / unobserved</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 border-t border-accent/15 p-5 md:grid-cols-2 md:px-6">
        <ReasonList title="Possible explanations" items={result.possible_explanations ?? []} />
        <ReasonList title="Recommended next checks" items={result.next_checks ?? []} />
      </div>
      {result.guardrail ? <div className="border-t border-accent/15 px-5 py-3 text-[11px] leading-5 text-muted md:px-6">{result.guardrail}</div> : null}
    </section>
  );
}

function Metric({ label, value, icon }: { label: string; value: number; icon?: React.ReactNode }) {
  return <div className="rounded-xl border border-border bg-surface p-3.5"><div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[.14em] text-faint">{icon}{label}</div><div className="mt-1.5 text-2xl font-semibold text-text">{value}</div></div>;
}

function ReasonList({ title, items }: { title: string; items: string[] }) {
  return <div><div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{title}</div><div className="mt-2 space-y-1.5">{items.slice(0, 6).map((item) => <div key={item} className="text-xs leading-5 text-muted">• {item}</div>)}</div></div>;
}
