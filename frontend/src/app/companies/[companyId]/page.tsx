import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Building2, FileText, GitBranch, NotebookPen } from "lucide-react";

import { Section, StatCard, SurfaceCard } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/states";
import { Timeline } from "@/components/ui/timeline";
import {
  getCompanyAwards,
  getCompanyOverview,
  getCompanyTenders,
  type CompanyTenderHistoryItem,
  type CompanyTenderSort
} from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import { CompanyInvestigationControls } from "./company-investigation-controls";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ companyId: string }>;
  searchParams: Promise<{
    limit?: string;
    offset?: string;
    q?: string;
    sort?: string;
  }>;
};

const tenderSorts = new Set<CompanyTenderSort>(["latest", "published_date", "value", "title", "award_value"]);

export default async function CompanyInvestigationPage({ params, searchParams }: PageProps) {
  const [{ companyId }, queryParams] = await Promise.all([params, searchParams]);
  const limit = parsePositiveInt(queryParams.limit, 25, 100);
  const offset = parseNonNegativeInt(queryParams.offset, 0);
  const query = (queryParams.q ?? "").trim();
  const sort = parseSort(queryParams.sort);

  const [overview, tenders, awards] = await Promise.all([
    getCompanyOverview(companyId).catch(handleNotFound),
    getCompanyTenders(companyId, { limit, offset, q: query || undefined, sort }).catch(handleNotFound),
    getCompanyAwards(companyId, 25, 0).catch(handleNotFound)
  ]);

  const timelineItems = [
    { label: "First procurement", value: formatDate(overview.first_procurement_date) },
    { label: "Latest procurement", value: formatDate(overview.latest_procurement_date) },
    { label: "Company added", value: formatDate(overview.company.created_at) },
    { label: "Record updated", value: formatDate(overview.company.updated_at) }
  ];

  const sortableHref = (nextSort: CompanyTenderSort) => {
    const next = new URLSearchParams({
      limit: String(limit),
      offset: "0",
      sort: nextSort
    });
    if (query) next.set("q", query);
    return `?${next.toString()}`;
  };

  const columns: Column<CompanyTenderHistoryItem>[] = [
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
      header: "Buyer",
      render: (tender) => <span className="text-[#C8CDD3]">{tender.buyer ?? "Unknown"}</span>
    },
    {
      key: "value",
      header: "Tender Value",
      sortHref: sortableHref("value"),
      align: "right",
      render: (tender) => (
        <span className="font-semibold tabular-nums text-[#E6E8EB]">
          {formatMoney(tender.tender_value, tender.currency)} {tender.currency}
        </span>
      )
    },
    {
      key: "published",
      header: "Published",
      sortHref: sortableHref("published_date"),
      render: (tender) => <span className="text-[#C8CDD3]">{formatDate(tender.publication_date)}</span>
    },
    {
      key: "status",
      header: "Status",
      render: (tender) => <span className="text-[#9AA4AF]">{tender.procurement_status ?? "Not stored"}</span>
    }
  ];

  return (
    <main className="min-h-screen bg-[#0B0F14]">
      <section className="border-b border-[#2A3441] bg-[#121821]">
        <div className="mx-auto w-full max-w-7xl px-5 py-7 sm:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <nav className="text-xs text-[#9AA4AF]">
                <Link className="hover:text-[#E6E8EB]" href="/">
                  Dashboard
                </Link>
                <span className="px-2">/</span>
                <span>Company Investigation</span>
              </nav>
              <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-[#C58B2A]">Company File</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#E6E8EB]">{overview.company.name}</h1>
              <p className="mt-2 text-sm text-[#9AA4AF]">{overview.registration_identifier ?? "No registration identifier"}</p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[4px] border border-[#2A3441] bg-[#171F2A] px-4 text-sm font-semibold text-[#E6E8EB] transition hover:border-[#C58B2A]"
              href={`/graph?company_id=${companyId}&depth=2`}
            >
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              Open graph
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-5 px-5 py-6 sm:px-8 xl:grid-cols-[360px_1fr]">
        <aside className="space-y-5">
          <Section eyebrow="Overview" title="Company Information">
            <InfoRow label="Name" value={overview.company.name} />
            <InfoRow label="Identifier" value={overview.registration_identifier ?? "Not available"} />
            <InfoRow label="Address" value={overview.address ?? "Not available"} />
            <InfoRow label="Added" value={formatDate(overview.company.created_at)} />
          </Section>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <StatCard label="Total Tenders" value={formatInteger(overview.total_tenders)} tone="accent" />
            <StatCard label="Awards Won" value={formatInteger(overview.total_awards_won)} tone="success" />
            <StatCard label="Procurement Value" value={`${formatMoney(overview.total_procurement_value, "UAH")} UAH`} tone="warning" />
            <StatCard label="Average Award" value={`${formatMoney(overview.average_award_value, "UAH")} UAH`} />
          </div>

          <SurfaceCard className="p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB]">
              <NotebookPen className="h-4 w-4 text-[#C58B2A]" aria-hidden="true" />
              Notes
            </div>
            <div className="mt-4">
              <EmptyState title="No analyst notes" message="Notes can be attached to this company file when available." />
            </div>
          </SurfaceCard>
        </aside>

        <div className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <Section eyebrow="Statistics" title="Investigation Summary">
              <div className="grid gap-3 sm:grid-cols-2">
                <Metric label="First procurement" value={formatDate(overview.first_procurement_date)} />
                <Metric label="Latest procurement" value={formatDate(overview.latest_procurement_date)} />
                <Metric label="Awards indexed" value={formatInteger(awards.pagination.total)} />
                <Metric label="Tender history" value={formatInteger(tenders.pagination.total)} />
              </div>
            </Section>

            <SurfaceCard className="p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB]">
                <Building2 className="h-4 w-4 text-[#667A52]" aria-hidden="true" />
                Related Entities
              </div>
              <div className="mt-4">
                <EmptyState title="Graph-derived entities" message="Open the graph to inspect connected buyers, tenders, and awards." />
              </div>
            </SurfaceCard>
          </div>

          <CompanyInvestigationControls limit={limit} offset={offset} query={query} sort={sort} total={tenders.pagination.total} />

          <Section eyebrow="History" title="Tender History">
            <DataTable
              columns={columns}
              empty={<EmptyState message={query ? "No tenders match this company search." : "No tender history is available for this company."} />}
              getHref={(tender) => `/tenders/${tender.id}`}
              items={tenders.items}
            />
          </Section>

          <Section eyebrow="Outcome" title="Awards">
            {awards.items.length === 0 ? (
              <EmptyState message="No awards have been recorded for this company." />
            ) : (
              <div className="grid gap-3">
                {awards.items.map((award) => (
                  <div className="grid gap-3 rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4 md:grid-cols-[1fr_auto]" key={award.id}>
                    <div>
                      <Link className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB] hover:text-[#F3D59A]" href={`/tenders/${award.tender_id}`}>
                        <Award className="h-4 w-4 text-[#C58B2A]" aria-hidden="true" />
                        {award.tender_title}
                      </Link>
                      <div className="mt-1 text-xs text-[#9AA4AF]">{award.tender_reference_number}</div>
                    </div>
                    <div className="text-left md:text-right">
                      <div className="text-sm font-semibold tabular-nums text-[#E6E8EB]">
                        {formatMoney(award.award_amount, award.currency)} {award.currency}
                      </div>
                      <div className="mt-1 text-xs text-[#9AA4AF]">{formatDate(award.award_date)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <Section eyebrow="Timeline" title="Activity Timeline">
              <Timeline items={timelineItems} />
            </Section>
            <Section eyebrow="Evidence" title="Evidence">
              <EmptyState title="No evidence attached" message="Documents, screenshots, and analyst evidence can be attached here when available." />
            </Section>
          </div>
        </div>
      </section>
    </main>
  );
}

function handleNotFound(error: unknown): never {
  if (error instanceof Error && error.message === "not_found") {
    notFound();
  }
  throw error;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-[#2A3441] py-3 first:pt-0 last:border-b-0 last:pb-0">
      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{label}</div>
      <div className="mt-1 text-sm text-[#E6E8EB]">{value}</div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3">
      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{label}</div>
      <div className="mt-2 text-sm font-semibold text-[#E6E8EB]">{value}</div>
    </div>
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

function parseSort(value: string | undefined): CompanyTenderSort {
  return tenderSorts.has(value as CompanyTenderSort) ? (value as CompanyTenderSort) : "latest";
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("en").format(value);
}
