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
import { RoleCommandCenter } from "@/components/dashboard/role-command-center";
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

      <RoleCommandCenter />

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
                  <span className="min-w-0 flex-1 truncate text-[13px] text-text">{supplier.company}</span>
                  <span className="shrink-0 tabular text-xs text-muted">{formatCompactMoney(String(supplier.total_value))}</span>
                </Link>
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Activity" title="Recent investigation signals">
          <LiveActivityFeed timeline={timeline} />
        </Section>
      </Reveal>

      <Reveal className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Section eyebrow="Trend" title="Award activity">
          <AreaTrend
            labels={trend.map((point) => point.month)}
            series={[{ name: "Awarded value", data: trend.map((point) => Number(point.total_awarded_value) || 0), color: CHART.success }]}
            height={240}
            valueFormatter={(value) => formatCompactMoney(String(value))}
          />
        </Section>
        <Section eyebrow="Sources" title="Data source status">
          <SourceStatus sources={overview.sources} />
        </Section>
      </Reveal>
    </div>
  );
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg-2/50 px-3.5 py-3">
      <div className="text-[9px] font-semibold uppercase tracking-[0.12em] text-faint">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular text-text">{value}</div>
    </div>
  );
}

function ActionLink({ href, icon, title, detail }: { href: string; icon: React.ReactNode; title: string; detail: string }) {
  return (
    <Link href={href} className="group flex items-center gap-3 border-r border-border p-4 transition hover:bg-surface-2 last:border-r-0">
      <span className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-accent transition group-hover:border-accent/30">{icon}</span>
      <span className="min-w-0"><span className="block text-sm font-medium text-text">{title}</span><span className="mt-0.5 block text-xs text-faint">{detail}</span></span>
    </Link>
  );
}
