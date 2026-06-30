import Link from "next/link";
import { FileText, GitBranch } from "lucide-react";

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
          <div className="font-semibold text-[#E6E8EB]">{tender.title}</div>
          <div className="mt-1 text-xs text-[#9AA4AF]">{tender.reference_number}</div>
        </div>
      )
    },
    {
      key: "buyer",
      header: "Procuring Entity",
      render: (tender) => <span className="text-[#C8CDD3]">{tender.procuring_entity ?? "Unknown"}</span>
    },
    {
      key: "value",
      header: "Value",
      sortHref: sortableHref("value"),
      align: "right",
      render: (tender) => (
        <span className="font-semibold tabular-nums text-[#E6E8EB]">
          {formatMoney(tender.estimated_value, tender.currency)} {tender.currency}
        </span>
      )
    },
    {
      key: "published",
      header: "Published",
      sortHref: sortableHref("published_date"),
      render: (tender) => <span className="text-[#C8CDD3]">{formatDate(tender.published_date)}</span>
    }
  ];

  return (
    <main className="min-h-screen bg-[#0B0F14]">
      <section className="border-b border-[#2A3441] bg-[#121821]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-7 sm:px-8">
          <nav className="text-xs text-[#9AA4AF]">
            <Link className="hover:text-[#E6E8EB]" href="/">
              Dashboard
            </Link>
            <span className="px-2">/</span>
            <span>Tenders</span>
          </nav>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#C58B2A]">Procurement Records</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#E6E8EB]">Tenders</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[#9AA4AF]">
                Search and sort tender records by title, procuring entity, value, or publication date.
              </p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[4px] border border-[#2A3441] bg-[#171F2A] px-4 text-sm font-semibold text-[#E6E8EB] transition hover:border-[#C58B2A]"
              href="/graph"
            >
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              Graph
            </Link>
          </div>
          <div className="text-xs text-[#9AA4AF]">{tenders.pagination.total} total records</div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl space-y-5 px-5 py-6 sm:px-8">
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
          <div className="flex items-center gap-2 text-xs text-[#9AA4AF]">
            <FileText className="h-4 w-4 text-[#C58B2A]" aria-hidden="true" />
            Showing {tenders.items.length} records from offset {offset}.
          </div>
        ) : null}
      </section>
    </main>
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
