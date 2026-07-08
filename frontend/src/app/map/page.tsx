import { Info, MapPin } from "lucide-react";
import { getGeography } from "@/lib/api";
import { PageHeader, PageShell, RankBar } from "@/components/ui/page";
import { Section, StatCard } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatCompactMoney, formatNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function MapPage() {
  let data;
  try {
    data = await getGeography();
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Analysis" title="Geography" />
        <ErrorState message="Could not compute the geographic distribution." />
      </PageShell>
    );
  }

  const attributed = data.regions.filter((r) => r.region !== "Unattributed");
  const maxTenders = Math.max(1, ...attributed.map((r) => r.tenders));
  const coverage = data.total > 0 ? Math.round((data.matched / data.total) * 100) : 0;

  return (
    <PageShell>
      <PageHeader
        eyebrow="Analysis"
        title="Procurement Geography"
        subtitle="Regional distribution of tenders inferred from buyer names and tender titles."
      />

      <div className="mb-5 flex items-start gap-2 rounded-[14px] border border-info/30 bg-info/5 px-4 py-3 text-xs text-muted">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" />
        <span>
          Regions are derived by matching Indian state and union-territory names inside procuring-entity and
          tender titles. {formatNumber(data.matched)} of {formatNumber(data.total)} tenders ({coverage}%) were
          attributed; the remainder are grouped as <strong className="text-text">Unattributed</strong>.
        </span>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Attributed regions" value={String(attributed.length)} tone="accent" icon={<MapPin className="h-4 w-4" />} />
        <StatCard label="Matched tenders" value={formatNumber(data.matched)} tone="success" />
        <StatCard label="Unattributed" value={formatNumber(data.unmatched)} tone="warning" />
        <StatCard label="Coverage" value={`${coverage}%`} />
      </div>

      <Section eyebrow="Distribution" title="Tenders by region">
        {attributed.length === 0 ? (
          <EmptyState icon={<MapPin className="h-5 w-5" />} title="No regions attributed" message="No state or UT names were found in buyer records." />
        ) : (
          <div className="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
            {attributed.map((r) => (
              <RankBar
                key={r.region}
                label={r.region}
                value={r.tenders}
                max={maxTenders}
                meta={`${r.tenders} tenders · ${formatCompactMoney(r.value)}`}
              />
            ))}
          </div>
        )}
      </Section>
    </PageShell>
  );
}
