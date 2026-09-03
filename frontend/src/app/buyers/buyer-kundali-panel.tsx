"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, BarChart3, Building2, CalendarDays, ShieldCheck, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/ui/states";
import { SeverityBadge } from "@/components/ui/page";
import { formatMoneyFull } from "@/lib/format";
import { EASE } from "@/lib/motion";

type Distribution = {
  dimension: string;
  name: string;
  count: number;
  share: string;
  value: string;
  rank: number;
  population_count: number;
};

type Kundali = {
  profile: {
    name: string;
    normalized_name: string;
    tender_count: number;
    awarded_tender_count: number;
    first_tender_date: string | null;
    latest_tender_date: string | null;
  };
  metrics: Array<{ label: string; value: string }>;
  supplier_concentration: Distribution[];
  category_distribution: Distribution[];
  geography_distribution: Distribution[];
  method_distribution: Distribution[];
  supplier_relationships: Array<{
    supplier_id: string;
    supplier_name: string;
    award_count: number;
    award_share: string;
    award_value: string;
    latest_award_date: string | null;
  }>;
  value_benchmark: {
    sample_size: number;
    minimum: string | null;
    p25: string | null;
    median: string | null;
    p75: string | null;
    maximum: string | null;
    currency: string | null;
    method: string;
  };
  submission_window: {
    sample_size: number;
    minimum_days: number | null;
    median_days: number | null;
    p75_days: number | null;
    maximum_days: number | null;
    unknown_count: number;
  };
  timeline: Array<{ period: string; tenders: number; awards: number; tender_value: string; award_value: string }>;
  award_estimate_distribution: Distribution | null;
  signals: Array<{
    type: string;
    severity: string;
    title: string;
    summary: string;
    evidence: string[];
    confidence: string;
    review_required: boolean;
  }>;
  data_quality: {
    tender_records: number;
    awarded_tenders: number;
    records_with_method: number;
    records_with_category: number;
    records_with_geography: number;
    records_with_deadline: number;
    records_with_award_value: number;
    records_with_source_url: number;
    bidder_level_status: string;
    cancellation_status: string;
    corrigendum_status: string;
    notes: string[];
  };
  limitations: string[];
};

export function BuyerKundaliPanel({ buyer }: { buyer: string }) {
  const [data, setData] = useState<Kundali | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ buyer });
    fetch(`/api/buyers/kundali?${params.toString()}`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("failed");
        return (await response.json()) as Kundali;
      })
      .then(setData)
      .catch((cause) => {
        if ((cause as Error).name !== "AbortError") setError(true);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [buyer]);

  const maxTimeline = useMemo(() => Math.max(...(data?.timeline.map((point) => point.tenders) ?? [1]), 1), [data]);

  if (loading) {
    return (
      <section className="rounded-[28px] border border-accent/15 bg-surface/80 p-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 animate-pulse rounded-2xl bg-accent/10" />
          <div className="space-y-2"><div className="h-3 w-28 animate-pulse rounded bg-bg-2" /><div className="h-5 w-64 animate-pulse rounded bg-bg-2" /></div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <div className="h-24 animate-pulse rounded-2xl border border-border bg-bg-2/60" key={index} />)}</div>
      </section>
    );
  }

  if (error || !data) {
    return <EmptyState title="Buyer intelligence unavailable" message="No matching buyer profile could be loaded from the indexed Indian procurement corpus." />;
  }

  return (
    <section className="space-y-5">
      <section className="relative overflow-hidden rounded-[30px] border border-accent/20 bg-surface p-6 shadow-[0_30px_100px_-60px_rgba(16,185,129,0.55)] md:p-7">
        <div className="pointer-events-none absolute inset-0 opacity-50 [background-image:linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] [background-size:28px_28px]" />
        <motion.div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-accent/12 blur-3xl" animate={{ scale: [1, 1.1, 1], opacity: [0.35, 0.6, 0.35] }} transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }} />
        <div className="relative">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent"><Sparkles className="h-3.5 w-3.5" /> Buyer Kundali</div>
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-bg-2/70 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint"><ShieldCheck className="h-3.5 w-3.5 text-accent" /> Evidence-aware</div>
          </div>
          <h2 className="mt-5 text-2xl font-semibold tracking-[-0.03em] text-text">Procurement fingerprint</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">Tender volume, supplier allocation, procurement methods, value baselines, submission windows, and longitudinal review leads for {data.profile.name}.</p>
        </div>
      </section>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {data.metrics.map((metric, index) => (
          <motion.div key={metric.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04, duration: 0.35, ease: EASE }} className="rounded-2xl border border-border bg-bg-2/70 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-faint">{metric.label}</div>
            <div className="mt-2 text-xl font-semibold tabular-nums text-text">{metric.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <DistributionCard title="Supplier concentration" icon={<Building2 className="h-4 w-4" />} rows={data.supplier_concentration} />
        <DistributionCard title="Procurement methods" icon={<BarChart3 className="h-4 w-4" />} rows={data.method_distribution} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <DistributionCard title="Category mix" icon={<BarChart3 className="h-4 w-4" />} rows={data.category_distribution} />
        <DistributionCard title="Geography mix" icon={<Building2 className="h-4 w-4" />} rows={data.geography_distribution} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <section className="rounded-2xl border border-border bg-surface p-5">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Value baseline</div>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[["P25", data.value_benchmark.p25], ["Median", data.value_benchmark.median], ["P75", data.value_benchmark.p75], ["Max", data.value_benchmark.maximum]].map(([label, value]) => (
              <div className="rounded-xl border border-border bg-bg-2 p-3" key={String(label)}><div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-faint">{label}</div><div className="mt-2 text-sm font-semibold text-text">{value ? formatMoneyFull(value, data.value_benchmark.currency ?? "INR") : "—"}</div></div>
            ))}
          </div>
          <div className="mt-3 text-xs text-muted">{data.value_benchmark.sample_size} tender values · {data.value_benchmark.method}</div>
          <div className="mt-3 rounded-xl border border-border bg-bg-2/50 p-3 text-xs leading-5 text-muted">Contextual baseline only. It is not a statutory threshold.</div>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Submission window</div>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <ValueTile label="Min" value={days(data.submission_window.minimum_days)} /><ValueTile label="Median" value={days(data.submission_window.median_days)} /><ValueTile label="P75" value={days(data.submission_window.p75_days)} /><ValueTile label="Max" value={days(data.submission_window.maximum_days)} />
          </div>
          <div className="mt-3 text-xs text-muted">{data.submission_window.sample_size} dated tenders · {data.submission_window.unknown_count} without both dates</div>
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-surface p-5">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-accent"><CalendarDays className="h-4 w-4" />Supplier allocation</div>
        <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-xs uppercase tracking-[0.1em] text-faint"><tr><th className="pb-3 pr-4">Supplier</th><th className="pb-3 pr-4 text-right">Awards</th><th className="pb-3 pr-4 text-right">Share</th><th className="pb-3 text-right">Award value</th></tr></thead><tbody>{data.supplier_relationships.slice(0, 12).map((row) => <tr className="border-t border-border" key={row.supplier_id}><td className="py-3 pr-4 font-medium text-text">{row.supplier_name}</td><td className="py-3 pr-4 text-right tabular-nums text-muted">{row.award_count}</td><td className="py-3 pr-4 text-right tabular-nums text-muted">{Number(row.award_share) * 100}%</td><td className="py-3 text-right font-semibold tabular-nums text-text">{formatMoneyFull(row.award_value)}</td></tr>)}</tbody></table></div>
      </section>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <section className="rounded-2xl border border-border bg-surface p-5">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Activity timeline</div>
          <div className="mt-4 space-y-2">{data.timeline.slice(-18).map((point) => <div className="grid grid-cols-[86px_1fr_auto] items-center gap-3" key={point.period}><div className="font-mono text-[11px] text-faint">{point.period}</div><div className="h-2 overflow-hidden rounded-full bg-bg-2"><motion.div initial={{ width: 0 }} animate={{ width: `${Math.max(7, (point.tenders / maxTimeline) * 100)}%` }} transition={{ duration: 0.6, ease: EASE }} className="h-full rounded-full bg-accent/70" /></div><div className="text-xs font-semibold tabular-nums text-text">{point.tenders}</div></div>)}</div>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Data quality</div>
          <div className="mt-4 space-y-3 text-sm text-muted"><Quality label="Method coverage" value={data.data_quality.records_with_method} total={data.data_quality.tender_records} /><Quality label="Category coverage" value={data.data_quality.records_with_category} total={data.data_quality.tender_records} /><Quality label="Deadline coverage" value={data.data_quality.records_with_deadline} total={data.data_quality.tender_records} /><Quality label="Source URL coverage" value={data.data_quality.records_with_source_url} total={data.data_quality.tender_records} /></div>
          <div className="mt-4 rounded-xl border border-border bg-bg-2/50 p-3 text-xs leading-5 text-muted">Bidder-level: <b className="text-text">{data.data_quality.bidder_level_status}</b><br />Cancellation: <b className="text-text">{data.data_quality.cancellation_status}</b><br />Corrigenda: <b className="text-text">{data.data_quality.corrigendum_status}</b></div>
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-surface p-5">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-accent"><AlertTriangle className="h-4 w-4" />Review signals</div>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">{data.signals.length ? data.signals.map((signal) => <div className="rounded-2xl border border-border bg-bg-2/70 p-4" key={`${signal.type}-${signal.title}`}><div className="flex items-start justify-between gap-3"><div className="flex items-center gap-2 text-sm font-semibold text-text">{signal.severity === "informational" ? <ShieldCheck className="h-4 w-4 text-accent" /> : <AlertTriangle className="h-4 w-4 text-warning" />}{signal.title}</div><SeverityBadge severity={signal.severity === "informational" ? "low" : (signal.severity as "low" | "medium" | "high")} /></div><p className="mt-2 text-sm leading-6 text-muted">{signal.summary}</p><div className="mt-3 flex flex-wrap gap-1.5"><span className="rounded-md border border-border bg-surface px-2 py-1 text-[10px] uppercase tracking-[0.1em] text-faint">confidence: {signal.confidence}</span>{signal.review_required ? <span className="rounded-md border border-warning/30 bg-warning/5 px-2 py-1 text-[10px] uppercase tracking-[0.1em] text-warning">review</span> : null}{signal.evidence.slice(0, 3).map((item) => <span key={item} className="rounded-md border border-border bg-surface px-2 py-1 text-[11px] text-muted">{item}</span>)}</div></div>) : <EmptyState message="No buyer review signals are currently emitted from the indexed data." />}</div>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5">
        <div className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">Coverage & limitations</div>
        <div className="mt-4 grid gap-2 md:grid-cols-2">{data.limitations.map((item) => <div className="rounded-xl border border-border bg-bg-2/40 p-3 text-xs leading-5 text-muted" key={item}>{item}</div>)}</div>
      </section>
    </section>
  );
}

function DistributionCard({ title, icon, rows }: { title: string; icon: React.ReactNode; rows: Distribution[] }) {
  return <section className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center gap-2 text-sm font-semibold text-text">{icon}{title}</div><div className="mt-4 space-y-3">{rows.length ? rows.slice(0, 7).map((row) => <div key={`${row.dimension}-${row.name}`}><div className="flex items-center justify-between gap-3 text-xs"><span className="truncate text-text">{row.name}</span><span className="font-semibold tabular-nums text-muted">{Number(row.share) * 100}%</span></div><div className="mt-1 h-2 overflow-hidden rounded-full bg-bg-2"><div className="h-full rounded-full bg-accent/60" style={{ width: `${Math.max(3, Number(row.share) * 100)}%` }} /></div></div>) : <EmptyState message="No classification data is available." />}</div></section>;
}

function ValueTile({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-border bg-bg-2 p-3"><div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-faint">{label}</div><div className="mt-2 text-sm font-semibold text-text">{value}</div></div>; }
function Quality({ label, value, total }: { label: string; value: number; total: number }) { return <div><div className="flex items-center justify-between"><span>{label}</span><span className="font-semibold text-text">{value}/{total}</span></div><div className="mt-1 h-1.5 overflow-hidden rounded-full bg-bg-2"><div className="h-full rounded-full bg-accent/60" style={{ width: `${total ? (value / total) * 100 : 0}%` }} /></div></div>; }
function days(value: number | null): string { return value === null ? "—" : `${value.toFixed(1)}d`; }
