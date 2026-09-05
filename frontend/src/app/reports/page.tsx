import { Activity, Building2, FileText, Landmark, TrendingUp } from "lucide-react";
import { AreaTrend, DonutChart, HBarChart } from "@/components/charts";
import { PageHeader, PageShell, RankBar } from "@/components/ui/page";
import { Section, StatCard } from "@/components/ui/card";
import { ErrorState, EmptyState } from "@/components/ui/states";
import { getAnalyticsOverview } from "@/lib/api";
import { formatCompactMoney, formatNumber } from "@/lib/format";
import { CHART_SERIES } from "@/lib/theme";

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  let data;
  try {
    data = await getAnalyticsOverview();
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Analysis" title="Reports" />
        <ErrorState message="SENTRY could not build the portfolio report. Check the data connection and retry." />
      </PageShell>
    );
  }

  const { totals, top_buyers, top_suppliers, monthly, sources } = data;
  const maxBuyer = Math.max(1, ...top_buyers.map((b) => Number(b.total_value) || 0));
  const maxSource = Math.max(1, ...sources.map((s) => s.tenders));
  const distributionSlices = sources.slice(0, 6).map((s, index) => ({
    name: s.source_name,
    value: s.tenders,
    color: CHART_SERIES[index % CHART_SERIES.length]
  }));
  const controlChecks = [
    { label: "Bid participation coverage", value: 0, max: Math.max(1, totals.tenders), meta: "Unavailable in current source records", tone: "info" as const },
    { label: "Award coverage", value: totals.awards, max: Math.max(1, totals.tenders), meta: `${formatNumber(totals.awards)} award records`, tone: "success" as const },
    { label: "Supplier coverage", value: totals.companies, max: Math.max(1, totals.buyers + totals.companies), meta: `${formatNumber(totals.companies)} supplier entities`, tone: "info" as const }
  ];

  return (
    <PageShell>
      <PageHeader
        eyebrow="Analysis"
        title="Portfolio Reports"
        subtitle="Aggregate analytics across the indexed Indian procurement dataset. International records may remain stored for provenance, but are excluded from portfolio metrics."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Tenders" value={formatNumber(totals.tenders)} tone="accent" icon={<FileText className="h-4 w-4" />} />
        <StatCard label="Awarded value" value={formatCompactMoney(totals.total_awarded_value)} tone="success" icon={<TrendingUp className="h-4 w-4" />} />
        <StatCard label="Buyers" value={formatNumber(totals.buyers)} icon={<Landmark className="h-4 w-4" />} />
        <StatCard label="Bid participation" value="N/A" tone="neutral" meta="Bidder-level records not exposed by current sources" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Section eyebrow="Trend" title="Procurement value by month">
            {monthly.length === 0 ? <EmptyState message="No dated tender records are available for this chart." /> : <AreaTrend categories={monthly.map((m) => m.month.slice(2))} values={monthly.map((m) => Number(m.value) || 0)} height={260} valueFormatter={(v) => formatCompactMoney(String(v))} />}
          </Section>
        </div>
        <Section eyebrow="Sources" title="Records by source">
          {sources.length === 0 ? <EmptyState message="No source records are available." /> : <div className="space-y-3">{sources.map((s) => <RankBar key={s.source_name} label={s.source_name} value={s.tenders} max={maxSource} meta={formatNumber(s.tenders)} tone="info" />)}</div>}
        </Section>
        <Section eyebrow="Distribution" title="Indian procurement distribution">
          {distributionSlices.length === 0 ? <EmptyState message="No distribution data is available." /> : <div className="grid gap-4 sm:grid-cols-[220px_1fr] lg:grid-cols-1"><DonutChart slices={distributionSlices} centerValue={formatNumber(totals.tenders)} centerLabel="Indian tenders" height={210} /><div className="space-y-2">{distributionSlices.map((slice) => <div className="flex items-center gap-2 text-sm" key={slice.name}><span className="h-2.5 w-2.5 rounded-sm" style={{ background: slice.color }} /><span className="min-w-0 flex-1 truncate text-muted">{slice.name}</span><span className="tabular font-semibold text-text">{formatNumber(slice.value)}</span></div>)}</div></div>}
        </Section>
        <Section eyebrow="Concentration" title="Top buyers by awarded value">
          {top_buyers.length === 0 ? <EmptyState message="No buyer records are available." /> : <div className="space-y-3.5">{top_buyers.map((b) => <RankBar key={b.buyer} label={b.buyer} value={Number(b.total_value) || 0} max={maxBuyer} meta={`${formatCompactMoney(b.total_value)} · ${b.awards} awards`} />)}</div>}
        </Section>
        <Section eyebrow="Suppliers" title="Top suppliers by awarded value">
          {top_suppliers.length === 0 ? <EmptyState message="No supplier records are available." /> : <HBarChart labels={top_suppliers.slice(0, 8).map((s) => s.name)} values={top_suppliers.slice(0, 8).map((s) => Number(s.total_value) || 0)} color="#3ec08a" height={260} valueFormatter={(v) => formatCompactMoney(String(v))} />}
        </Section>
        <Section eyebrow="Coverage" title="Dataset summary">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Metric icon={<FileText className="h-4 w-4" />} label="Tenders" value={formatNumber(totals.tenders)} />
            <Metric icon={<Building2 className="h-4 w-4" />} label="Suppliers" value={formatNumber(totals.companies)} />
            <Metric icon={<Activity className="h-4 w-4" />} label="Awards" value={formatNumber(totals.awards)} />
            <Metric icon={<Landmark className="h-4 w-4" />} label="Buyers" value={formatNumber(totals.buyers)} />
            <Metric label="Total tender value" value={formatCompactMoney(totals.total_tender_value)} />
            <Metric label="Average tender value" value={formatCompactMoney(totals.average_tender_value)} />
          </div>
        </Section>
        <Section eyebrow="Data quality" title="Coverage checks">
          <div className="space-y-3.5">{controlChecks.map((check) => <RankBar key={check.label} label={check.label} value={check.value} max={check.max} meta={check.meta} tone={check.tone} />)}</div>
          <p className="mt-4 text-[11px] leading-relaxed text-faint">Bidder participation is not inferred from winner-only award records. Where source data does not expose bidder-level participation, SENTRY reports the capability as unavailable rather than treating missing data as a negative finding.</p>
        </Section>
      </div>
    </PageShell>
  );
}

function Metric({ icon, label, value }: { icon?: React.ReactNode; label: string; value: string }) {
  return <div className="rounded-lg border border-border bg-bg-2/40 p-3"><div className="flex items-center gap-1.5 text-[11px] text-faint">{icon}{label}</div><div className="mt-1 tabular text-lg font-semibold text-text">{value}</div></div>;
}
