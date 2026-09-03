"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, BarChart3, Building2, CalendarDays, ShieldCheck, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/ui/states";
import { SeverityBadge } from "@/components/ui/page";
import { formatMoneyFull } from "@/lib/format";
import { EASE } from "@/lib/motion";


type Metric = {
  label: string;
  value: string;
  detail: string | null;
  availability: "available" | "insufficient_data" | "not_indexed";
};

type Concentration = {
  dimension: string;
  name: string;
  count: number;
  share: string;
  value: string;
  rank: number;
  population_count: number;
};

type Signal = {
  type: string;
  severity: "low" | "medium" | "high" | "informational";
  title: string;
  summary: string;
  evidence: string[];
  confidence: "high" | "moderate" | "low" | "unknown";
  review_required: boolean;
};

type Kundali = {
  profile: { name: string };
  metrics: Metric[];
  buyer_concentration: Concentration[];
  category_concentration: Concentration[];
  geography_concentration: Concentration[];
  method_concentration: Concentration[];
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
  timeline: Array<{ period: string; awards: number; value: string }>;
  repeat_winner: {
    repeat_buyer_relationships: number;
    highest_buyer_share: string;
    highest_buyer: string | null;
    max_consecutive_awards_at_buyer: number;
    interpretation: string;
  };
  signals: Signal[];
  data_quality: {
    award_records: number;
    tender_records: number;
    sourced_records: number;
    records_with_source_url: number;
    records_with_retrieval_timestamp: number;
    participation_status: string;
    bidder_level_status: string;
    debarment_status: string;
    notes: string[];
  };
  limitations: string[];
};

export function SupplierKundaliPanel() {
  const [data, setData] = useState<Kundali | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const companyId = parts[0] === "companies" ? parts[1] : null;
    if (!companyId) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    fetch(`/api/companies/${companyId}/kundali`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("failed");
        return (await response.json()) as Kundali;
      })
      .then((payload) => setData(payload))
      .catch((cause) => {
        if ((cause as Error).name !== "AbortError") setError(true);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, []);

  const maxTimelineAwards = useMemo(
    () => Math.max(...(data?.timeline.map((point) => point.awards) ?? [1]), 1),
    [data]
  );

  if (loading) {
    return (
      <section className="rounded-[28px] border border-accent/15 bg-surface/80 p-5 md:p-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 animate-pulse rounded-2xl bg-accent/10" />
          <div className="space-y-2">
            <div className="h-3 w-28 animate-pulse rounded bg-bg-2" />
            <div className="h-5 w-52 animate-pulse rounded bg-bg-2" />
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div className="h-24 animate-pulse rounded-2xl border border-border bg-bg-2/60" key={index} />
          ))}
        </div>
      </section>
    );
  }

  if (error || !data) {
    return <EmptyState title="Supplier intelligence unavailable" message="The supplier kundali could not be loaded from the current procurement corpus." />;
  }

  return (
    <section className="space-y-5">
      <div className="relative overflow-hidden rounded-[30px] border border-accent/20 bg-surface p-6 shadow-[0_30px_100px_-60px_rgba(16,185,129,0.55)] md:p-7">
        <div className="pointer-events-none absolute inset-0 opacity-50 [background-image:linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] [background-size:28px_28px]" />
        <motion.div
          className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-accent/12 blur-3xl"
          animate={{ scale: [1, 1.1, 1], opacity: [0.35, 0.6, 0.35] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        />
        <div className="relative">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
              <Sparkles className="h-3.5 w-3.5" /> Supplier Kundali
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-bg-2/70 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
              <ShieldCheck className="h-3.5 w-3.5 text-accent" /> Evidence-aware
            </div>
          </div>
          <div className="mt-5 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold tracking-[-0.03em] text-text">Longitudinal supplier profile</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Recorded awards, buyer concentration, market dimensions, value distribution and known data gaps — without treating missing bidder data as a finding.
              </p>
            </div>
            <Building2 className="hidden h-10 w-10 text-accent/70 sm:block" aria-hidden="true" />
          </div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {data.metrics.map((metric, index) => (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.35, ease: EASE }}
            className="rounded-2xl border border-border bg-bg-2/70 p-4"
            key={metric.label}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-faint">{metric.label}</div>
              {metric.availability !== "available" ? <span className="text-[9px] uppercase tracking-[0.12em] text-warning">{metric.availability.replace("_", " ")}</span> : null}
            </div>
            <div className="mt-2 text-xl font-semibold tabular-nums text-text">{metric.value}</div>
            {metric.detail ? <div className="mt-1 text-xs leading-5 text-muted">{metric.detail}</div> : null}
          </motion.div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <ConcentrationCard title="Buyer concentration" icon={<Building2 className="h-4 w-4" />} rows={data.buyer_concentration} />
        <ConcentrationCard title="Category mix" icon={<BarChart3 className="h-4 w-4" />} rows={data.category_concentration} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <Section title="Award value distribution" eyebrow="Benchmark context">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["P25", data.value_benchmark.p25],
              ["Median", data.value_benchmark.median],
              ["P75", data.value_benchmark.p75],
              ["Max", data.value_benchmark.maximum]
            ].map(([label, value]) => (
              <div className="rounded-2xl border border-border bg-bg-2 p-3" key={String(label)}>
                <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">{label}</div>
                <div className="mt-2 text-sm font-semibold text-text">{value ? formatMoneyFull(value) : "—"}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-muted">{data.value_benchmark.sample_size} award values · {data.value_benchmark.method}</div>
          <div className="mt-4 rounded-xl border border-border bg-bg-2/50 p-3 text-xs leading-5 text-muted">
            This is descriptive supplier history, not a statutory benchmark or a misconduct threshold.
          </div>
        </Section>

        <Section title="Repeat winner context" eyebrow="Relationship layer">
          <div className="grid gap-3 sm:grid-cols-2">
            <ContextMetric label="Repeat buyer relationships" value={String(data.repeat_winner.repeat_buyer_relationships)} />
            <ContextMetric label="Highest buyer share" value={`${Number(data.repeat_winner.highest_buyer_share) * 100}%`} />
            <ContextMetric label="Highest buyer" value={data.repeat_winner.highest_buyer ?? "Not available"} />
            <ContextMetric label="Max awards at one buyer" value={String(data.repeat_winner.max_consecutive_awards_at_buyer)} />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted">{data.repeat_winner.interpretation}</p>
        </Section>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <Section title="Supplier activity" eyebrow="Timeline">
          {data.timeline.length === 0 ? (
            <EmptyState message="No dated award activity is available." />
          ) : (
            <div className="space-y-2">
              {data.timeline.slice(-18).map((point) => (
                <div className="grid grid-cols-[90px_1fr_auto] items-center gap-3" key={point.period}>
                  <div className="font-mono text-[11px] text-faint">{point.period}</div>
                  <div className="h-2 overflow-hidden rounded-full bg-bg-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(7, (point.awards / maxTimelineAwards) * 100)}%` }}
                      transition={{ duration: 0.6, ease: EASE }}
                      className="h-full rounded-full bg-accent/70"
                    />
                  </div>
                  <div className="text-xs font-semibold tabular-nums text-text">{point.awards}</div>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section title="Data quality" eyebrow="Integrity">
          <div className="space-y-3 text-sm">
            <QualityRow label="Award records" value={data.data_quality.award_records} />
            <QualityRow label="Tender records" value={data.data_quality.tender_records} />
            <QualityRow label="With source URL" value={data.data_quality.records_with_source_url} />
            <QualityRow label="With retrieval timestamp" value={data.data_quality.records_with_retrieval_timestamp} />
            <div className="rounded-xl border border-border bg-bg-2/50 p-3 text-xs leading-5 text-muted">
              Participation: <span className="font-semibold text-text">{data.data_quality.participation_status}</span><br />
              Bidder-level: <span className="font-semibold text-text">{data.data_quality.bidder_level_status}</span><br />
              Debarment: <span className="font-semibold text-text">{data.data_quality.debarment_status}</span>
            </div>
          </div>
        </Section>
      </div>

      <Section title="Review signals" eyebrow="Investigator leads">
        <div className="grid gap-3 lg:grid-cols-2">
          {data.signals.map((signal) => (
            <div className="rounded-2xl border border-border bg-bg-2/70 p-4" key={`${signal.type}-${signal.title}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-text">
                  {signal.severity === "informational" ? <ShieldCheck className="h-4 w-4 text-accent" /> : <AlertTriangle className="h-4 w-4 text-warning" />}
                  {signal.title}
                </div>
                <SeverityBadge severity={signal.severity === "informational" ? "low" : signal.severity} />
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{signal.summary}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <span className="rounded-md border border-border bg-surface px-2 py-1 text-[10px] uppercase tracking-[0.1em] text-faint">confidence: {signal.confidence}</span>
                {signal.review_required ? <span className="rounded-md border border-warning/30 bg-warning/5 px-2 py-1 text-[10px] uppercase tracking-[0.1em] text-warning">review</span> : null}
                {signal.evidence.slice(0, 3).map((item) => <span className="rounded-md border border-border bg-surface px-2 py-1 text-[11px] text-muted" key={item}>{item}</span>)}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Coverage & limitations" eyebrow="What the system knows">
        <div className="grid gap-2 md:grid-cols-2">
          {data.limitations.map((limitation) => (
            <div className="rounded-xl border border-border bg-bg-2/40 p-3 text-xs leading-5 text-muted" key={limitation}>{limitation}</div>
          ))}
        </div>
      </Section>
    </section>
  );
}

function ConcentrationCard({ title, icon, rows }: { title: string; icon: React.ReactNode; rows: Concentration[] }) {
  return (
    <Section title={title} eyebrow="Market shape">
      {rows.length === 0 ? <EmptyState message="No classification data is available." /> : (
        <div className="space-y-3">
          {rows.slice(0, 6).map((row) => (
            <div key={`${row.dimension}-${row.name}`}>
              <div className="flex items-center justify-between gap-3 text-xs">
                <div className="flex min-w-0 items-center gap-2 text-text">{icon}<span className="truncate">{row.name}</span></div>
                <div className="font-semibold tabular-nums text-muted">{Number(row.share) * 100}%</div>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-bg-2">
                <div className="h-full rounded-full bg-accent/55" style={{ width: `${Math.max(2, Number(row.share) * 100)}%` }} />
              </div>
              <div className="mt-1 text-[10px] text-faint">{row.count} awards · {formatMoneyFull(row.value)}</div>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function Section({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{eyebrow}</div>
      <div className="mt-1 text-base font-semibold text-text">{title}</div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function ContextMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg-2 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-faint">{label}</div>
      <div className="mt-2 truncate text-sm font-semibold text-text">{value}</div>
    </div>
  );
}

function QualityRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border pb-2 last:border-b-0 last:pb-0">
      <span className="text-muted">{label}</span>
      <span className="font-semibold tabular-nums text-text">{value}</span>
    </div>
  );
}
