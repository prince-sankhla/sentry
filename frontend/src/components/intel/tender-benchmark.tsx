"use client";

import { useEffect, useState, type ReactNode } from "react";
import { BarChart3, Database, Info, Loader2, TrendingUp } from "lucide-react";

import { formatMoney } from "@/lib/format";

type BenchmarkData = {
  tender_id: string;
  reference_number: string;
  metric: string;
  observed_value: string | number | null;
  currency: string | null;
  benchmark_available: boolean;
  population: { level: string; dimensions: Record<string, string>; sample_size: number; sufficient_sample: boolean };
  statistics: { minimum: string | number | null; p25: string | number | null; median: string | number | null; mean: string | number | null; p75: string | number | null; maximum: string | number | null; iqr: string | number | null; percentile: number | null; deviation_iqr: string | number | null };
  interpretation: string;
};

export function TenderBenchmark({ tenderId }: { tenderId: string }) {
  const [data, setData] = useState<BenchmarkData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";
    fetch(`${backendUrl}/api/benchmarks/tender/${tenderId}`, { cache: "no-store", headers: { Accept: "application/json" } })
      .then(async (response) => {
        if (!response.ok) throw new Error("benchmark_unavailable");
        return response.json();
      })
      .then((next) => { if (active) setData(next as BenchmarkData); })
      .catch(() => { if (active) setData(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [tenderId]);

  if (loading) {
    return <div className="flex items-center gap-2 rounded-2xl border border-border bg-bg-2/40 p-4 text-sm text-muted"><Loader2 className="h-4 w-4 animate-spin text-accent" /> Building comparable-market baseline…</div>;
  }
  if (!data) return <div className="rounded-2xl border border-border bg-bg-2/40 p-4 text-sm text-faint">Benchmark comparison is unavailable for this tender.</div>;

  const s = data.statistics;
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-bg-2/40 p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-text"><BarChart3 className="h-4 w-4 text-accent" /> Market Benchmark</div>
            <div className="mt-1 text-xs text-faint">{data.population.sample_size} comparable Indian tenders · {data.population.level}</div>
          </div>
          <div className="text-right"><div className="text-[10px] uppercase tracking-[0.14em] text-faint">Observed</div><div className="mt-1 text-xl font-semibold tabular-nums text-text">{formatMoney(data.observed_value, data.currency ?? "INR")} {data.currency ?? ""}</div></div>
        </div>
      </div>

      {!data.benchmark_available ? (
        <div className="rounded-2xl border border-border bg-surface p-4 text-sm text-muted">{data.interpretation}</div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="P25" value={s.p25} currency={data.currency} />
            <Stat label="Median" value={s.median} currency={data.currency} emphasized />
            <Stat label="P75" value={s.p75} currency={data.currency} />
            <Stat label="Percentile" value={s.percentile == null ? null : `${s.percentile}th`} plain icon={<TrendingUp className="h-3.5 w-3.5" />} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-border bg-surface p-4"><div className="text-[10px] uppercase tracking-[0.15em] text-faint">Distribution</div><div className="mt-3 space-y-2 text-xs text-muted"><Row label="Minimum" value={formatMoney(s.minimum, data.currency ?? "INR")} /><Row label="Mean" value={formatMoney(s.mean, data.currency ?? "INR")} /><Row label="Maximum" value={formatMoney(s.maximum, data.currency ?? "INR")} /><Row label="IQR" value={formatMoney(s.iqr, data.currency ?? "INR")} /></div></div>
            <div className="rounded-2xl border border-border bg-surface p-4"><div className="text-[10px] uppercase tracking-[0.15em] text-faint">Interpretation</div><p className="mt-3 text-sm leading-6 text-muted">{data.interpretation}</p>{s.deviation_iqr != null ? <div className="mt-3 rounded-xl border border-border bg-bg-2/50 px-3 py-2 text-xs text-faint">Deviation from median: <span className="font-semibold text-text">{Number(s.deviation_iqr).toFixed(2)} IQR</span></div> : null}</div>
          </div>
        </>
      )}

      <div className="rounded-xl border border-border bg-bg-2/30 p-3 text-[11px] leading-relaxed text-faint"><div className="flex items-center gap-2 font-semibold text-muted"><Database className="h-3.5 w-3.5" /> Population scope</div><div className="mt-1">{Object.entries(data.population.dimensions).map(([key, value]) => `${key}: ${value}`).join(" · ") || "Global Indian procurement corpus"}</div><div className="mt-2 flex items-start gap-2"><Info className="mt-0.5 h-3 w-3 shrink-0" />Percentile and IQR are contextual statistics. They are not statutory thresholds or findings of misconduct.</div></div>
    </div>
  );
}

function Stat({ label, value, currency, emphasized, plain, icon }: { label: string; value: string | number | null | undefined; currency?: string | null; emphasized?: boolean; plain?: boolean; icon?: ReactNode }) {
  return <div className={`rounded-2xl border p-4 ${emphasized ? "border-accent/30 bg-accent/[0.06]" : "border-border bg-surface"}`}><div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{icon}{label}</div><div className="mt-2 text-lg font-semibold tabular-nums text-text">{value == null ? "—" : plain ? value : `${formatMoney(value, currency ?? "INR")} ${currency ?? ""}`}</div></div>;
}
function Row({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-3"><span>{label}</span><span className="font-semibold tabular-nums text-text">{value}</span></div>; }
