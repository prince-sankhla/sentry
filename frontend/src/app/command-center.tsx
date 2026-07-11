"use client";

/**
 * SENTRY Command Center — the flagship intelligence dashboard.
 *
 * Rendered when the Investigation Workspace has no active query. Consumes the
 * existing analytics/dashboard/risk endpoints (no backend changes) and lays them
 * out at reference density: KPI row, India procurement map centerpiece, risk
 * donut, live activity, source status (Indian-first), top buyers/suppliers,
 * recent records, and a procurement timeline rail.
 */
import { motion } from "framer-motion";
import {
  Award,
  Building2,
  FileText,
  Landmark,
  Radar,
  ShieldAlert,
  Zap
} from "lucide-react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AreaTrend, DonutChart, HBarChart } from "@/components/charts";
import { CHART } from "@/components/charts/echart";
import { Section } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { SeverityBadge } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { AiStatus } from "@/components/dashboard/ai-status";
import { LiveActivityFeed } from "@/components/dashboard/live-activity";
import { MorningBrief } from "@/components/dashboard/morning-brief";
import { SourceStatus } from "@/components/dashboard/source-status";
import { Reveal } from "@/components/intel/reveal";
import {
  getAnalyticsOverview,
  getAnalyticsTimeline,
  getDashboardRecent,
  getGeography,
  getRisk,
  type AnalyticsOverview,
  type DashboardRecent,
  type GeographyResponse,
  type RiskResponse,
  type TimelineResponse
} from "@/lib/api";
import { formatCompactMoney, formatDate, formatNumber } from "@/lib/format";

// India map is heavy (SVG topojson) — lazy-load, client only.
const IndiaMap = dynamic(() => import("@/components/map/india-map").then((m) => m.IndiaMap), {
  ssr: false,
  loading: () => <div className="grid h-[460px] place-items-center text-sm text-faint">Loading India procurement map…</div>
});

type Bundle = {
  overview: AnalyticsOverview;
  recent: DashboardRecent;
  risk: RiskResponse;
  geo: GeographyResponse;
  timeline: TimelineResponse;
};

export function CommandCenter() {
  const router = useRouter();
  const [data, setData] = useState<Bundle | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all([
      getAnalyticsOverview(),
      getDashboardRecent(6),
      getRisk(),
      getGeography(),
      getAnalyticsTimeline(40)
    ])
      .then(([overview, recent, risk, geo, timeline]) => {
        if (alive) setData({ overview, recent, risk, geo, timeline });
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  const launch = useCallback(
    (q: string) => router.push(`/?q=${encodeURIComponent(q)}`),
    [router]
  );

  if (failed) return <div className="mt-6"><ErrorState message="Could not load the command center." /></div>;
  if (!data) return <CommandCenterSkeleton />;

  return <CommandCenterView data={data} onLaunch={launch} />;
}

function CommandCenterView({ data, onLaunch }: { data: Bundle; onLaunch: (q: string) => void }) {
  const { overview, recent, risk, geo, timeline } = data;
  const t = overview.totals;

  const riskSlices = useMemo(
    () => [
      { name: "High", value: risk.summary.high, color: CHART.danger },
      { name: "Medium", value: risk.summary.medium, color: CHART.warning },
      { name: "Low", value: Math.max(risk.summary.low, risk.summary.total - risk.summary.high - risk.summary.medium), color: CHART.success }
    ],
    [risk]
  );

  const topBuyers = overview.top_buyers.slice(0, 6);
  const topSuppliers = overview.top_suppliers.slice(0, 6);

  // Procurement value trend — last 12 months of awarded/tender value.
  const trend = useMemo(() => overview.monthly.slice(-12), [overview.monthly]);

  return (
    <div className="mt-2 space-y-5">
      <MorningBrief overview={overview} risk={risk} timeline={timeline} onLaunch={onLaunch} />

      {/* KPI ROW — every figure is a live total from the analytics API. We
          deliberately show NO period-over-period delta pill here: the backend
          exposes no historical baseline, and this is a grounded-evidence product
          (see AiInvestigationPanel: "nothing here is fabricated"). Inventing a
          "+18.6% vs last 30 days" would be the one unsourced number on the board.
          The sparklines are ambient shape only — they assert no specific claim. */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard label="Total Tenders" value={formatNumber(t.tenders)} tone="accent" icon={<FileText className="h-4 w-4" />} spark={spark(t.tenders)} />
        <KpiCard label="Awarded Value" value={formatCompactMoney(t.total_awarded_value)} tone="success" icon={<Award className="h-4 w-4" />} spark={spark(9)} />
        <KpiCard label="Buyers" value={formatNumber(t.buyers)} tone="info" icon={<Landmark className="h-4 w-4" />} spark={spark(6)} />
        <KpiCard label="Suppliers" value={formatNumber(t.companies)} icon={<Building2 className="h-4 w-4" />} spark={spark(7)} />
        <KpiCard label="High-Risk" value={formatNumber(risk.summary.high)} tone="danger" icon={<ShieldAlert className="h-4 w-4" />} spark={spark(5)} />
        <KpiCard label="Single-Bidder" value={formatNumber(t.single_bidder_tenders)} tone="danger" icon={<Radar className="h-4 w-4" />} spark={spark(4)} />
      </div>

      {/* MAP + RISK + INVESTIGATIONS */}
      <Reveal className="grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
        <Section eyebrow="Geography" title="Procurement Activity Across India" action={<Link href="/map" className="text-xs text-accent hover:underline">Full map →</Link>}>
          <IndiaMap regions={geo.regions} height={460} />
        </Section>

        <div className="space-y-5">
          <Section eyebrow="Risk" title="Risk Overview" action={<Link href="/risk" className="text-xs text-accent hover:underline">Monitor →</Link>}>
            <div className="grid grid-cols-[1fr_auto] items-center gap-4">
              <DonutChart slices={riskSlices} centerValue={formatNumber(risk.summary.high)} centerLabel="High Risk" height={200} />
              <ul className="space-y-2.5 pr-2">
                {riskSlices.map((s) => (
                  <li key={s.name} className="flex items-center gap-2 text-sm">
                    <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
                    <span className="text-muted">{s.name}</span>
                    <span className="ml-auto tabular font-semibold text-text">{formatNumber(s.value)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Section>

          <Section eyebrow="Intelligence" title="Recent Investigations" action={<Link href="/investigations" className="text-xs text-accent hover:underline">View all →</Link>}>
            <ul className="space-y-2">
              {risk.signals.slice(0, 5).map((s, i) => (
                <li key={i}>
                  <Link
                    href={s.supplier_id ? `/companies/${s.supplier_id}` : s.tender_id ? `/tenders/${s.tender_id}` : "/risk"}
                    className="flex items-center justify-between gap-3 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm text-text">{s.supplier_name ?? s.title}</span>
                      <span className="block truncate text-xs text-faint">{s.buyer ?? s.summary}</span>
                    </span>
                    <SeverityBadge severity={s.severity} score={s.score} />
                  </Link>
                </li>
              ))}
            </ul>
          </Section>
        </div>
      </Reveal>

      {/* TOP BUYERS + SUPPLIERS + LIVE ACTIVITY */}
      <Reveal className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Section eyebrow="Concentration" title="Top Buyers by Award Value" action={<Link href="/reports" className="text-xs text-accent hover:underline">View all →</Link>}>
          {topBuyers.length === 0 ? <EmptyState message="No buyer data." /> : (
            <HBarChart
              labels={topBuyers.map((b) => truncate(b.buyer, 22))}
              values={topBuyers.map((b) => Number(b.total_value) || 0)}
              color={CHART.accent}
              height={220}
              valueFormatter={(v) => formatCompactMoney(String(v))}
            />
          )}
        </Section>

        <Section eyebrow="Suppliers" title="Top Suppliers by Award Value" action={<Link href="/companies" className="text-xs text-accent hover:underline">View all →</Link>}>
          {topSuppliers.length === 0 ? <EmptyState message="No supplier data." /> : (
            <ul className="space-y-1">
              {topSuppliers.map((s) => (
                <li key={s.company_id}>
                  <Link href={`/companies/${s.company_id}`} className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 transition hover:bg-surface-2">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-border bg-bg-2 text-success"><Building2 className="h-3.5 w-3.5" /></span>
                      <span className="truncate text-sm text-text">{s.name}</span>
                    </span>
                    <span className="shrink-0 tabular text-sm font-semibold text-text">{formatCompactMoney(s.total_value)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section eyebrow="Live" title="Live Activity Feed" action={<span className="inline-flex items-center gap-1.5 text-[11px] text-success"><span className="h-1.5 w-1.5 rounded-full bg-success pulse-live" />Live</span>}>
          <LiveActivityFeed timeline={timeline.events} recent={recent} />
        </Section>
      </Reveal>

      {/* PROCUREMENT TRENDS + AI INVESTIGATION STATUS */}
      <Reveal className="grid grid-cols-1 gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Section
          eyebrow="Trends"
          title="Procurement Value Trend"
          action={<Link href="/reports" className="text-xs text-accent hover:underline">Analytics →</Link>}
        >
          {trend.length === 0 ? (
            <EmptyState message="No dated procurement records to chart." />
          ) : (
            <AreaTrend
              categories={trend.map((m) => m.month.slice(2))}
              values={trend.map((m) => Number(m.value) || 0)}
              color={CHART.accent}
              height={220}
              valueFormatter={(v) => formatCompactMoney(String(v))}
            />
          )}
        </Section>

        <Section
          eyebrow="Reasoning"
          title="AI Investigation Status"
          action={<Link href="/investigations" className="text-xs text-accent hover:underline">Investigate →</Link>}
        >
          <AiStatus />
        </Section>
      </Reveal>

      {/* SOURCES + RECENT TENDERS */}
      <Reveal className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Section eyebrow="Ingestion" title="Data Sources" action={<Link href="/settings" className="text-xs text-accent hover:underline">Status →</Link>}>
          <SourceStatus sources={overview.sources} />
        </Section>

        <div className="lg:col-span-2">
          <Section eyebrow="Records" title="Recent Tenders" action={<Link href="/tenders" className="text-xs text-accent hover:underline">View all →</Link>}>
            <ul className="divide-y divide-border">
              {recent.latest_tenders.map((tender) => (
                <li key={tender.id}>
                  <Link href={`/tenders/${tender.id}`} className="flex items-center justify-between gap-4 py-2.5 transition hover:opacity-90">
                    <span className="flex min-w-0 items-center gap-3">
                      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-info"><FileText className="h-4 w-4" /></span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-text">{tender.title}</span>
                        <span className="block truncate text-xs text-faint">{tender.procuring_entity ?? "Unknown buyer"} · {formatDate(tender.published_date)}</span>
                      </span>
                    </span>
                    <span className="shrink-0 tabular text-sm font-semibold text-text">{formatCompactMoney(tender.estimated_value, tender.currency)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Section>
        </div>
      </Reveal>
    </div>
  );
}

/* ---- helpers ---- */

function truncate(s: string | null, n: number): string {
  if (!s) return "Unknown";
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

/** Deterministic pseudo-sparkline seed (no Math.random — SSR-safe). */
function spark(seed: number): number[] {
  const out: number[] = [];
  let v = 40 + (seed % 7) * 6;
  for (let i = 0; i < 12; i++) {
    v += ((i * 7 + seed * 13) % 11) - 4;
    out.push(Math.max(8, v));
  }
  return out;
}

const BOOT_LINES = [
  "Connecting to Indian procurement sources…",
  "Synchronising GeM · CPPP · NIC feeds…",
  "Scoring risk indicators…",
  "Assembling morning brief…"
];

function CommandCenterSkeleton() {
  const [line, setLine] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setLine((l) => (l + 1) % BOOT_LINES.length), 900);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mt-2 space-y-5">
      {/* brief hero shell with a live boot log — reads as "coming online" */}
      <div className="relative overflow-hidden rounded-[22px] border border-border bg-surface/80 p-6 md:p-8">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
          <Zap className="h-3.5 w-3.5" /> Morning Intelligence Brief
        </div>
        <div className="mt-4 h-7 w-2/3 shimmer rounded-lg" />
        <div className="mt-2 h-7 w-1/2 shimmer rounded-lg" />
        <div className="mt-5 flex items-center gap-2 text-sm text-muted">
          <span className="h-2 w-2 rounded-full bg-accent pulse-live" />
          <motion.span
            key={line}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-faint"
          >
            {BOOT_LINES[line]}
          </motion.span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="shimmer h-[104px] rounded-2xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
        <div className="shimmer h-[540px] rounded-2xl" />
        <div className="space-y-5">
          <div className="shimmer h-[280px] rounded-2xl" />
          <div className="shimmer h-[240px] rounded-2xl" />
        </div>
      </div>
    </div>
  );
}
