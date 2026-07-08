import Link from "next/link";
import { FileText, GitBranch } from "lucide-react";

import { PageHeader, PageShell } from "@/components/ui/page";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/states";
import { getTenders, type TenderSort, type TenderSummary } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import { TenderSearchControls } from "../tender-search-controls";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    limit?: string;
    offset?: string;
    q?: string;
    sort?: string;
  }>;
};

const tenderSorts = new Set<TenderSort>(["newest", "published_date", "value", "title"]);

export default async function TendersPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const limit = parsePositiveInt(params.limit, 25, 100);
  const offset = parseNonNegativeInt(params.offset, 0);
  const query = (params.q ?? "").trim();
  const sort = parseSort(params.sort);
  const tenders = await getTenders({ limit, offset, q: query || undefined, sort });

  const sortableHref = (nextSort: TenderSort) => {
    const next = new URLSearchParams({
      limit: String(limit),
      offset: "0",
      sort: nextSort
    });
    if (query) next.set("q", query);
    return `/tenders?${next.toString()}`;
  };

  const columns: Column<TenderSummary>[] = [
    {
      key: "tender",
      header: "Tender",
      sortHref: sortableHref("title"),
      render: (tender) => (
        <div>
          <div className="font-semibold text-text">{tender.title}</div>
          <div className="mt-1 font-mono text-xs text-faint">{tender.reference_number}</div>
        </div>
      )
    },
    {
      key: "buyer",
      header: "Procuring Entity",
      render: (tender) => <span className="text-muted">{tender.procuring_entity ?? "Unknown"}</span>
    },
    {
      key: "value",
      header: "Value",
      sortHref: sortableHref("value"),
      align: "right",
      render: (tender) => (
        <span className="font-semibold tabular-nums text-text">
          {formatMoney(tender.estimated_value, tender.currency)} {tender.currency}
        </span>
      )
    },
    {
      key: "published",
      header: "Published",
      sortHref: sortableHref("published_date"),
      render: (tender) => <span className="text-muted">{formatDate(tender.published_date)}</span>
    }
  ];

  return (
    <PageShell>
      <PageHeader
        eyebrow="Procurement Records"
        title="Tenders"
        subtitle="Search and sort tender records by title, procuring entity, value, or publication date."
        breadcrumb={[{ label: "Dashboard", href: "/" }, { label: "Tenders" }]}
        actions={
          <Link
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong"
            href="/graph"
          >
            <GitBranch className="h-4 w-4" aria-hidden="true" />
            Graph
          </Link>
        }
      />

      <div className="space-y-5">
        <TenderSearchControls limit={limit} offset={offset} query={query} sort={sort} total={tenders.pagination.total} />

        <DataTable
          columns={columns}
          empty={
            <EmptyState
              title="No tenders found"
              message={query ? "Try a different search term or clear the search box." : "Imported tender records will appear here."}
            />
          }
          getHref={(tender) => `/tenders/${tender.id}`}
          items={tenders.items}
        />

        {tenders.items.length > 0 ? (
          <div className="flex items-center gap-2 text-xs text-faint">
            <FileText className="h-4 w-4 text-accent" aria-hidden="true" />
            Showing {tenders.items.length} records from offset {offset}.
          </div>
        ) : null}
      </div>
    </PageShell>
  );
}

function parsePositiveInt(value: string | undefined, fallback: number, max: number): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return fallback;
  }
  return Math.min(parsed, max);
}

function parseNonNegativeInt(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

function parseSort(value: string | undefined): TenderSort {
  return tenderSorts.has(value as TenderSort) ? (value as TenderSort) : "newest";
}
