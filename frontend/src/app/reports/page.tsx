import { Activity, Building2, FileText, Landmark, TrendingUp } from "lucide-react";
import { getAnalyticsOverview } from "@/lib/api";
import { PageHeader, PageShell, RankBar } from "@/components/ui/page";
import { Section, StatCard } from "@/components/ui/card";
import { ErrorState, EmptyState } from "@/components/ui/states";
import { formatCompactMoney, formatNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  let data;
  try {
    data = await getAnalyticsOverview();
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Analysis" title="Reports" />
        <ErrorState message="Could not build the portfolio report." />
      </PageShell>
    );
  }

  const { totals, top_buyers, top_suppliers, monthly, sources } = data;
  const maxMonthly = Math.max(1, ...monthly.map((m) => Number(m.value) || 0));
  const maxBuyer = Math.max(1, ...top_buyers.map((b) => Number(b.total_value) || 0));
  const maxSupplier = Math.max(1, ...top_suppliers.map((s) => Number(s.total_value) || 0));
  const maxSource = Math.max(1, ...sources.map((s) => s.tenders));

  return (
    <PageShell>
      <PageHeader
        eyebrow="Analysis"
        title="Portfolio Reports"
        subtitle="Aggregate procurement analytics across all imported tenders, awards, buyers, and suppliers."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Tenders" value={formatNumber(totals.tenders)} tone="accent" icon={<FileText className="h-4 w-4" />} />
        <StatCard label="Awarded value" value={formatCompactMoney(totals.total_awarded_value)} tone="success" icon={<TrendingUp className="h-4 w-4" />} />
        <StatCard label="Buyers" value={formatNumber(totals.buyers)} icon={<Landmark className="h-4 w-4" />} />
        <StatCard label="Single-bidder" value={formatNumber(totals.single_bidder_tenders)} tone="danger" meta="tenders with one supplier" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Section eyebrow="Trend" title="Procurement value by month">
            {monthly.length === 0 ? (
              <EmptyState message="No dated tenders available to chart." />
            ) : (
              <div className="flex h-52 items-end gap-1.5">
                {monthly.map((m) => {
                  const h = Math.max(4, Math.round(((Number(m.value) || 0) / maxMonthly) * 100));
                  return (
                    <div key={m.month} className="group flex flex-1 flex-col items-center gap-2">
                      <div className="relative flex w-full flex-1 items-end">
                        <div
                          className="w-full rounded-t bg-gradient-to-t from-accent/30 to-accent/70 transition group-hover:from-accent/50 group-hover:to-accent"
                          style={{ height: `${h}%` }}
                        >
                          <div className="pointer-events-none absolute -top-8 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-elevated px-2 py-1 text-[11px] text-text group-hover:block">
                            {formatCompactMoney(m.value)} · {m.tenders} tenders
                          </div>
                        </div>
                      </div>
                      <span className="text-[10px] text-faint">{m.month.slice(2)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </Section>
        </div>

        <Section eyebrow="Sources" title="Records by source">
          {sources.length === 0 ? (
            <EmptyState message="No source data." />
          ) : (
            <div className="space-y-3">
              {sources.map((s) => (
                <RankBar
                  key={s.source_name}
                  label={s.source_name}
                  value={s.tenders}
                  max={maxSource}
                  meta={`${s.tenders}`}
                  tone="info"
                />
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Concentration" title="Top buyers by awarded value">
          {top_buyers.length === 0 ? (
            <EmptyState message="No buyer data." />
          ) : (
            <div className="space-y-3.5">
              {top_buyers.map((b) => (
                <RankBar
                  key={b.buyer}
                  label={b.buyer}
                  value={Number(b.total_value) || 0}
                  max={maxBuyer}
                  meta={`${formatCompactMoney(b.total_value)} · ${b.awards} awards`}
                />
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Suppliers" title="Top suppliers by awarded value">
          {top_suppliers.length === 0 ? (
            <EmptyState message="No supplier data." />
          ) : (
            <div className="space-y-3.5">
              {top_suppliers.map((s) => (
                <RankBar
                  key={s.company_id}
                  label={s.name}
                  value={Number(s.total_value) || 0}
                  max={maxSupplier}
                  meta={`${formatCompactMoney(s.total_value)} · ${s.awards} awards`}
                  href={`/companies/${s.company_id}`}
                  tone="success"
                />
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Coverage" title="Dataset summary">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Metric icon={<FileText className="h-4 w-4" />} label="Tenders" value={formatNumber(totals.tenders)} />
            <Metric icon={<Building2 className="h-4 w-4" />} label="Companies" value={formatNumber(totals.companies)} />
            <Metric icon={<Activity className="h-4 w-4" />} label="Awards" value={formatNumber(totals.awards)} />
            <Metric icon={<Landmark className="h-4 w-4" />} label="Buyers" value={formatNumber(totals.buyers)} />
            <Metric label="Total tender value" value={formatCompactMoney(totals.total_tender_value)} />
            <Metric label="Avg. tender" value={formatCompactMoney(totals.average_tender_value)} />
          </div>
        </Section>
      </div>
    </PageShell>
  );
}

function Metric({
  icon,
  label,
  value
}: {
  icon?: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-2/40 p-3">
      <div className="flex items-center gap-1.5 text-[11px] text-faint">
        {icon}
        {label}
      </div>
      <div className="mt-1 tabular text-lg font-semibold text-text">{value}</div>
    </div>
  );
}
