import { Award as AwardIcon } from "lucide-react";
import Link from "next/link";
import { getAwards } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { ListControls } from "@/components/ui/list-controls";
import { StatCard } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState, ErrorState } from "@/components/ui/states";
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
        <ErrorState message="Could not reach the awards service." />
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
          <div className="truncate font-mono text-[11px] text-faint">
            {a.company.registration_number ?? "—"}
          </div>
        </div>
      )
    },
    {
      key: "tender",
      header: "Tender",
      render: (a) => (
        <div className="min-w-0">
          <div className="truncate text-sm text-text">{a.tender.title}</div>
          <div className="truncate font-mono text-[11px] text-faint">
            {a.tender.reference_number}
          </div>
        </div>
      )
    },
    {
      key: "buyer",
      header: "Buyer",
      render: (a) => (
        <span className="text-sm text-muted">{a.tender.procuring_entity ?? "—"}</span>
      )
    },
    {
      key: "date",
      header: "Award date",
      render: (a) => <span className="text-sm text-muted">{formatDate(a.award_date)}</span>
    },
    {
      key: "value",
      header: "Value",
      align: "right",
      render: (a) => (
        <span className="tabular text-sm font-semibold text-text">
          {formatMoneyFull(a.award_value, a.currency)}
        </span>
      )
    }
  ];

  return (
    <PageShell>
      <PageHeader
        eyebrow="Records"
        title="Awards"
        subtitle="Contract awards linking suppliers to procuring buyers across all imported sources."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total awards" value={data.stats.total_awards.toLocaleString()} tone="accent" icon={<AwardIcon className="h-4 w-4" />} />
        <StatCard label="Awarded value" value={formatCompactMoney(data.stats.total_value, "INR")} tone="success" />
        <StatCard label="Avg. award" value={formatCompactMoney(data.stats.average_value, "INR")} />
        <StatCard label="Suppliers · Buyers" value={`${data.stats.awarded_suppliers} · ${data.stats.awarding_buyers}`} />
      </div>

      <ListControls
        placeholder="Search supplier, tender, or reference…"
        sortOptions={SORTS}
        total={data.pagination.total}
        limit={limit}
        offset={offset}
      />

      <DataTable
        columns={columns}
        items={data.items}
        getHref={(a) => `/companies/${a.company.id}`}
        empty={
          <EmptyState
            icon={<AwardIcon className="h-5 w-5" />}
            title="No awards found"
            message={q ? `No awards match “${q}”.` : "No awards have been imported yet."}
          />
        }
      />

      <p className="mt-4 text-center text-xs text-faint">
        Rows link to the supplier profile. Explore relationships in the{" "}
        <Link href="/graph" className="text-accent hover:underline">
          Graph Explorer
        </Link>
        .
      </p>
    </PageShell>
  );
}
