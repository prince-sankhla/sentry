import { Award as AwardIcon } from "lucide-react";
import Link from "next/link";
import { getAwards } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { ListControls } from "@/components/ui/list-controls";
import { StatCard } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { InvestigateAction } from "@/components/intel/investigate-action";
import { formatCompactMoney, formatDate, formatMoneyFull } from "@/lib/format";
import type { AwardListItem, AwardSort } from "@/lib/api";

export const dynamic = "force-dynamic";

const SORTS: { value: AwardSort; label: string }[] = [
  { value: "newest", label: "Most recent" },
  { value: "amount", label: "Highest value" },
  { value: "award_date", label: "Award date" },
  { value: "buyer", label: "Buyer" }
];

export default async function AwardsPage({
  searchParams
}: {
  searchParams: Promise<{ q?: string; offset?: string; sort?: AwardSort }>;
}) {
  const sp = await searchParams;
  const q = sp.q?.trim() || undefined;
  const limit = 25;
  const offset = Math.max(0, Number(sp.offset ?? 0) || 0);
  const sort = sp.sort ?? "newest";

  let data;
  try {
    data = await getAwards({ limit, offset, q, sort });
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Records" title="Awards" />
        <ErrorState message="SENTRY could not retrieve award records. Check the data connection and retry." />
      </PageShell>
    );
  }

  const columns: Column<AwardListItem>[] = [
    {
      key: "company",
      header: "Supplier",
      render: (a) => (
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-text">{a.company.name}</div>
          <div className="truncate font-mono text-[11px] text-faint">{a.company.registration_number ?? "Registration not available"}</div>
        </div>
      )
    },
    {
      key: "tender",
      header: "Tender",
      render: (a) => (
        <div className="min-w-0">
          <div className="truncate text-sm text-text">{a.tender.title}</div>
          <div className="truncate font-mono text-[11px] text-faint">{a.tender.reference_number}</div>
        </div>
      )
    },
    {
      key: "buyer",
      header: "Procuring entity",
      render: (a) => <span className="text-sm text-muted">{a.tender.procuring_entity ?? "Not available"}</span>
    },
    {
      key: "date",
      header: "Award date",
      render: (a) => <span className="text-sm text-muted">{formatDate(a.award_date)}</span>
    },
    {
      key: "value",
      header: "Award value",
      align: "right",
      render: (a) => (
        <span className="tabular text-sm font-semibold text-text">{formatMoneyFull(a.award_value, a.currency)}</span>
      )
    }
  ];

  return (
    <PageShell>
      <PageHeader
        eyebrow="Records"
        title="Award Records"
        subtitle="Award records linking suppliers, procuring entities and tender notices within the indexed Indian procurement dataset."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Award records" value={data.stats.total_awards.toLocaleString()} tone="accent" icon={<AwardIcon className="h-4 w-4" />} />
        <StatCard label="Awarded value" value={formatCompactMoney(data.stats.total_value, "INR")} tone="success" />
        <StatCard label="Average award" value={formatCompactMoney(data.stats.average_value, "INR")} />
        <StatCard label="Suppliers · Buyers" value={`${data.stats.awarded_suppliers} · ${data.stats.awarding_buyers}`} />
      </div>

      <ListControls placeholder="Search supplier, tender, reference, or buyer…" sortOptions={SORTS} total={data.pagination.total} limit={limit} offset={offset} />

      <DataTable
        columns={columns}
        items={data.items}
        getHref={(a) => `/companies/${a.company.id}`}
        rowAction={(award) => (
          <div className="flex items-center gap-1">
            <InvestigateAction query={award.company.name} label="Supplier" variant="subtle" />
            <InvestigateAction query={award.tender.reference_number} label="Tender" variant="subtle" />
            {award.tender.procuring_entity ? <InvestigateAction query={award.tender.procuring_entity} label="Buyer" variant="subtle" /> : null}
          </div>
        )}
        empty={
          <EmptyState
            icon={<AwardIcon className="h-5 w-5" />}
            title="No award records found"
            message={q ? `No award records match “${q}”.` : "No award records are available in the current indexed dataset."}
            suggestions={
              q
                ? undefined
                : [
                    "Review tender records to identify awards and related entities",
                    "Load a source that publishes award information",
                    "Open an investigation from a verified supplier, buyer, or tender"
                  ]
            }
          />
        }
      />

      <p className="mt-4 text-center text-xs text-faint">
        Award records are scoped to Indian procurement sources. Use the row actions to move from an award to a supplier, tender, or procuring-entity investigation, then inspect relationships in the{" "}
        <Link href="/graph" className="text-accent hover:underline">Graph Explorer</Link>.
      </p>
    </PageShell>
  );
}
