"use client";

import {
  Activity,
  Award,
  Building2,
  FileText,
  Flag,
  Landmark,
  Radar,
  ShieldAlert,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

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

const IndiaMap = dynamic(() => import("@/components/map/india-map").then((m) => m.IndiaMap), {
  ssr: false,
  loading: () => (
    <div className="grid h-[420px] place-items-center text-sm text-faint">
      Loading India procurement map…
    </div>
  )
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
    (query: string) => router.push(`/investigate?q=${encodeURIComponent(query)}`),
    [router]
  );

  if (failed) {
    return (
      <div className="mt-6">
        <ErrorState
          message="SENTRY could not load the command center. Check the data connection and retry."
        />
      </div>
    );
  }

  if (!data) return <CommandCenterSkeleton />;

  return <CommandCenterView data={data} onLaunch={launch} />;
}

function CommandCenterView({
  data,
  onLaunch
}: {
  data: Bundle;
  onLaunch: (query: string) => void;
}) {
  const { overview, recent, risk, geo, timeline } = data;
  const totals = overview.totals;

  const riskSlices = useMemo(
    () => [
      { name: "High", value: risk.summary.high, color: CHART.danger },
      { name: "Medium", value: risk.summary.medium, color: CHART.warning },
      {
        name: "Low",
        value: Math.max(risk.summary.low, risk.summary.total - risk.summary.high - risk.summary.medium),
        color: CHART.success
      }
    ],
    [risk]
  );

  const topBuyers = overview.top_buyers.slice(0, 6);
  const topSuppliers = overview.top_suppliers.slice(0, 6);
  const trend = useMemo(() => overview.monthly.slice(-12), [overview.monthly]);
  const signalCount = risk.summary.total;
  const attentionCount = risk.summary.high + risk.summary.medium;

  return (
    <div className="space-y-5">
      <Reveal>
        <div className="overflow-hidden rounded-2xl border border-border bg-surface elevate">
          <div className="relative px-6 py-6 sm:px-7 sm:py-7">
            <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-accent/[0.06] blur-3xl" />
            <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-3xl">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent/[0.07] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent">
                    <span className="h-1.5 w-1.5 rounded-full bg-accent pulse-live" />
                    Live intelligence
                  </span>
                  <span className="text-[11px] text-faint">Indian procurement scope</span>
                </div>
                <h1 className="text-[28px] font-semibold tracking-[-0.035em] text-text sm:text-[34px]">
                  Procurement intelligence, built for investigation.
                </h1>
                <p className="mt-2.5 max-w-2xl text-sm leading-6 text-muted">
                  Start with what SENTRY knows, see what needs attention, then follow the evidence into a tender, buyer, supplier or relationship.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:min-w-[460px]">
                <QuickStat label="Review signals" value={formatNumber(signalCount)} />
                <QuickStat label="Need review" value={formatNumber(attentionCount)} />
                <QuickStat label="High severity" value={formatNumber(risk.summary.high)} />
                <QuickStat label="Sources" value={formatNumber(overview.sources.length)} />
              </div>
            </div>
          </div>

          <div className="grid border-t border-border bg-bg-2/30 sm:grid-cols-3">
            <ActionLink href="/risk" icon={<ShieldAlert className="h-4 w-4" />} title="Review signals" detail="Prioritised screening queue" />
            <ActionLink href="/graph" icon={<Activity className="h-4 w-4" />} title="Trace relationships" detail="Connect entities and evidence" />
            <ActionLink href="/reports" icon={<Sparkles className="h-4 w-4" />} title="Explore the portfolio" detail="Patterns across the dataset" />
          </div>
        </div>
      </Reveal>

      <MorningBrief overview={overview} risk={risk} timeline={timeline} onLaunch={onLaunch} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <KpiCard href="/tenders" label="Tenders" value={formatNumber(totals.tenders)} tone="accent" icon={<FileText className="h-4 w-4" />} spark={spark(totals.tenders)} />
        <KpiCard href="/awards" label="Awarded value" value={formatCompactMoney(totals.total_awarded_value)} tone="success" icon={<Award className="h-4 w-4" />} spark={spark(9)} />
        <KpiCard href="/buyers" label="Buyers" value={formatNumber(totals.buyers)} tone="info" icon={<Landmark className="h-4 w-4" />} spark={spark(6)} />
        <KpiCard href="/companies" label="Suppliers" value={formatNumber(totals.companies)} icon={<Building2 className="h-4 w-4" />} spark={spark(7)} />
        <KpiCard href="/risk" label="Review signals" value={formatNumber(signalCount)} tone={risk.summary.high > 0 ? "danger" : "neutral"} icon={<Flag className="h-4 w-4" />} spark={spark(Math.max(signalCount, 1))} />
      </div>

      <Reveal className="grid grid-cols-1 gap-5 xl:grid-cols-[1.55fr_1fr]">
        <Section
          eyebrow="Geography"
          title="Procurement activity across India"
          action={<Link href="/map" className="text-xs font-medium text-accent hover:underline">Open full map →</Link>}
        >
          <IndiaMap regions={geo.regions} height={420} />
        </Section>

        <div className="space-y-5">
          <Section
            eyebrow="Priority queue"
            title={`${formatNumber(attentionCount)} signals need review`}
            action={<Link href="/risk" className="text-xs font-medium text-accent hover:underline">Open queue →</Link>}
          >
            {risk.signals.length === 0 ? (
              <EmptyState title="No active review signals" message="No screening signal currently falls within the selected scope." />
            ) : (
              <div className="space-y-2">
                {risk.signals.slice(0, 5).map((signal, index) => (
                  <Link
                    key={`${signal.title}-${index}`}
                    href={signal.supplier_id ? `/companies/${signal.supplier_id}` : signal.tender_id ? `/tenders/${signal.tender_id}` : "/risk"}
                    className="group flex items-center gap-3 rounded-xl border border-transparent px-3 py-3 transition hover:border-border hover:bg-surface-2"
                  >
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-warning">
                      <Flag className="h-3.5 w-3.5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] font-medium text-text">{signal.title}</span>
                      <span className="mt-0.5 block truncate text-[11px] text-faint">{signal.buyer ?? signal.supplier_name ?? signal.summary}</span>
                    </span>
                    <SeverityBadge severity={signal.severity} score={signal.score} />
                  </Link>
                ))}
              </div>
            )}
            <div className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-4">
              <QueueMetric label="High" value={risk.summary.high} tone="danger" />
              <QueueMetric label="Medium" value={risk.summary.medium} tone="warning" />
              <QueueMetric label="Low" value={riskSlices[2].value} tone="success" />
            </div>
          </Section>

          <Section eyebrow="Investigation engine" title="Reasoning status" action={<Link href="/investigations" className="text-xs font-medium text-accent hover:underline">Open workspace →</Link>}>
            <AiStatus />
          </Section>
        </div>
      </Reveal>

      <Reveal className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Section eyebrow="Relationships" title="Top buyers by awarded value" action={<Link href="/reports" className="text-xs font-medium text-accent hover:underline">View analysis →</Link>}>
          {topBuyers.length === 0 ? (
            <EmptyState message="No buyer records are available." />
          ) : (
            <HBarChart
              labels={topBuyers.map((buyer) => truncate(buyer.buyer, 22))}
              values={topBuyers.map((buyer) => Number(buyer.total_value) || 0)}
              color={CHART.accent}
              height={210}
              valueFormatter={(value) => formatCompactMoney(String(value))}
            />
          )}
        </Section>

        <Section eyebrow="Suppliers" title="Leading supplier relationships" action={<Link href="/companies" className="text-xs font-medium text-accent hover:underline">View suppliers →</Link>}>
          {topSuppliers.length === 0 ? (
            <EmptyState message="No supplier records are available." />
          ) : (
            <div className="space-y-1.5">
              {topSuppliers.map((supplier, index) => (
                <Link
                  key={supplier.company_id}
                  href={`/companies/${supplier.company_id}`}
                  className="flex items-center gap-3 rounded-xl px-2.5 py-2.5 transition hover:bg-surface-2"
                >
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-success text-[10px] font-semibold tabular">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[13px] text-text">{supplier.name}</span>
                  <span className="shrink-0 tabular text-xs font-semibold text-text">{formatCompactMoney(supplier.total_value)}</span>
                </Link>
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Activity" title="Recent procurement activity">
          <LiveActivityFeed timeline={timeline.events} recent={recent} />
        </Section>
      </Reveal>

      <Reveal className="grid grid-cols-1 gap-5 lg:grid-cols-[1.55fr_1fr]">
        <Section eyebrow="Trend" title="Procurement value over time" action={<Link href="/reports" className="text-xs font-medium text-accent hover:underline">Open reports →</Link>}>
          {trend.length === 0 ? (
            <EmptyState message="No dated procurement records are available to chart." />
          ) : (
            <AreaTrend
              categories={trend.map((month) => month.month.slice(2))}
              values={trend.map((month) => Number(month.value) || 0)}
              color={CHART.accent}
              height={220}
              valueFormatter={(value) => formatCompactMoney(String(value))}
            />
          )}
        </Section>

        <Section eyebrow="Data coverage" title="Source coverage">
          <SourceStatus sources={overview.sources} />
        </Section>
      </Reveal>

      <Reveal>
        <Section eyebrow="Records" title="Recent tender records" action={<Link href="/tenders" className="text-xs font-medium text-accent hover:underline">View all →</Link>}>
          <div className="divide-y divide-border">
            {recent.latest_tenders.length === 0 ? (
              <EmptyState message="No recent tender records are available." />
            ) : (
              recent.latest_tenders.map((tender) => (
                <Link key={tender.id} href={`/tenders/${tender.id}`} className="group flex items-center justify-between gap-4 py-3 transition hover:opacity-90">
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-info">
                      <FileText className="h-4 w-4" />
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-[13px] font-medium text-text">{tender.title}</span>
                      <span className="mt-0.5 block truncate text-[11px] text-faint">
                        {tender.procuring_entity ?? "Procuring entity not available"} · {formatDate(tender.published_date)}
                      </span>
                    </span>
                  </span>
                  <span className="shrink-0 tabular text-xs font-semibold text-text">{formatCompactMoney(tender.estimated_value, tender.currency)}</span>
                </Link>
              ))
            )}
          </div>
        </Section>
      </Reveal>
    </div>
  );
}

function ActionLink({ href, icon, title, detail }: { href: string; icon: ReactNode; title: string; detail: string }) {
  return (
    <Link href={href} className="group flex items-center gap-3 px-5 py-4 transition-colors hover:bg-surface-2/50">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent">{icon}</span>
      <span className="min-w-0">
        <span className="block text-xs font-semibold text-text">{title}</span>
        <span className="mt-0.5 block truncate text-[11px] text-faint">{detail}</span>
      </span>
    </Link>
  );
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg-2/40 px-3.5 py-3">
      <div className="t-label truncate">{label}</div>
      <div className="mt-1.5 tabular text-xl font-semibold tracking-[-0.02em] text-text">{value}</div>
    </div>
  );
}

function QueueMetric({ label, value, tone }: { label: string; value: number; tone: "danger" | "warning" | "success" }) {
  const colors = { danger: "text-danger", warning: "text-warning", success: "text-success" } as const;
  return (
    <div className="rounded-lg border border-border bg-bg-2/40 px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className={`mt-1 tabular text-lg font-semibold ${colors[tone]}`}>{formatNumber(value)}</div>
    </div>
  );
}

function truncate(value: string | null, length: number): string {
  if (!value) return "Not available";
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

function spark(seed: number): number[] {
  const points: number[] = [];
  let value = 36 + (seed % 9) * 5;
  for (let index = 0; index < 12; index += 1) {
    value += ((index * 11 + seed * 7) % 13) - 5;
    points.push(Math.max(10, value));
  }
  return points;
}

function CommandCenterSkeleton() {
  return (
    <div className="space-y-5" aria-hidden="true">
      <div className="rounded-2xl border border-border bg-surface p-7">
        <div className="h-3 w-28 animate-pulse rounded bg-bg-2" />
        <div className="mt-4 h-10 max-w-2xl animate-pulse rounded bg-bg-2" />
        <div className="mt-3 h-4 max-w-xl animate-pulse rounded bg-bg-2" />
        <div className="mt-7 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-20 animate-pulse rounded-xl bg-bg-2" />)}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-28 animate-pulse rounded-2xl border border-border bg-surface" />)}
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.55fr_1fr]">
        <div className="h-[490px] animate-pulse rounded-2xl border border-border bg-surface" />
        <div className="space-y-5">
          <div className="h-[320px] animate-pulse rounded-2xl border border-border bg-surface" />
          <div className="h-[170px] animate-pulse rounded-2xl border border-border bg-surface" />
        </div>
      </div>
    </div>
  );
}
