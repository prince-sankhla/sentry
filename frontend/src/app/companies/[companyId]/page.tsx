import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Building2, FileText, GitBranch, NotebookPen, ShieldAlert } from "lucide-react";

import { Section, StatCard, SurfaceCard } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/states";
import { Timeline } from "@/components/ui/timeline";
import {
  getCompanyAwards,
  getCompanyOverview,
  getCompanyTenders,
  type ProcurementIntelligenceSignal,
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
          <div className="font-semibold text-[#2F2F2F]">{tender.title}</div>
          <div className="mt-1 text-xs text-[#6B7280]">{tender.reference_number}</div>
        </div>
      )
    },
    {
      key: "buyer",
      header: "Buyer",
      render: (tender) => <span className="text-[#4B5563]">{tender.buyer ?? "Unknown"}</span>
    },
    {
      key: "value",
      header: "Tender Value",
      sortHref: sortableHref("value"),
      align: "right",
      render: (tender) => (
        <span className="font-semibold tabular-nums text-[#2F2F2F]">
          {formatMoney(tender.tender_value, tender.currency)} {tender.currency}
        </span>
      )
    },
    {
      key: "published",
      header: "Published",
      sortHref: sortableHref("published_date"),
      render: (tender) => <span className="text-[#4B5563]">{formatDate(tender.publication_date)}</span>
    },
    {
      key: "status",
      header: "Status",
      render: (tender) => <span className="text-[#6B7280]">{tender.procurement_status ?? "Not stored"}</span>
    }
  ];

  return (
    <main className="min-h-screen bg-[#FAF8F5] text-[#333333]">
      <section className="border-b border-[#E8D8B1] bg-white/95 backdrop-blur">
        <div className="mx-auto w-full max-w-[1600px] px-6 py-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <nav className="text-xs text-[#6B7280]">
                <Link className="hover:text-[#2F2F2F]" href="/">
                  Dashboard
                </Link>
                <span className="px-2">/</span>
                <span>Company Investigation</span>
              </nav>
              <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-[#B88927]">Company File</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#2F2F2F]">{overview.company.name}</h1>
              <p className="mt-2 text-sm text-[#6B7280]">{overview.registration_identifier ?? "No registration identifier"}</p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[16px] border border-[#E8D8B1] bg-white px-4 text-sm font-semibold text-[#2F2F2F] transition hover:border-[#D4A74B] hover:shadow-[0_16px_36px_rgba(87,63,14,0.08)]"
              href={`/graph?company_id=${companyId}&depth=2`}
            >
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              Open graph
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1600px] gap-5 px-6 py-6 xl:grid-cols-[360px_1fr] xl:px-8">
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
            <div className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F]">
              <NotebookPen className="h-4 w-4 text-[#B88927]" aria-hidden="true" />
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
              <div className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F]">
                <Building2 className="h-4 w-4 text-[#1E3A8A]" aria-hidden="true" />
                Related Entities
              </div>
              <div className="mt-4">
                <EmptyState title="Graph-derived entities" message="Open the graph to inspect connected buyers, tenders, and awards." />
              </div>
            </SurfaceCard>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <Section eyebrow="Phase 1" title="Procurement Intelligence">
              <IntelligenceSignals signals={overview.intelligence.signals} />
            </Section>

            <Section eyebrow="Scoring" title="Buyer-Supplier Scores">
              {overview.intelligence.relationship_scores.length === 0 ? (
                <EmptyState message="No relationship score is available for this company." />
              ) : (
                <div className="space-y-3">
                  {overview.intelligence.relationship_scores.map((relationship) => (
                    <div className="rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-3" key={`${relationship.buyer}-${relationship.supplier_id}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-[#2F2F2F]">{relationship.buyer ?? "Unknown buyer"}</div>
                          <div className="mt-1 text-xs text-[#6B7280]">
                            {relationship.awards_to_supplier} of {relationship.total_buyer_awards} awards
                          </div>
                        </div>
                        <div className="text-lg font-semibold tabular-nums text-[#8A6412]">{relationship.score}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>
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
                  <div className="grid gap-3 rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-4 md:grid-cols-[1fr_auto]" key={award.id}>
                    <div>
                      <Link className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F] hover:text-[#1E3A8A]" href={`/tenders/${award.tender_id}`}>
                        <Award className="h-4 w-4 text-[#D97706]" aria-hidden="true" />
                        {award.tender_title}
                      </Link>
                      <div className="mt-1 text-xs text-[#6B7280]">{award.tender_reference_number}</div>
                    </div>
                    <div className="text-left md:text-right">
                      <div className="text-sm font-semibold tabular-nums text-[#2F2F2F]">
                        {formatMoney(award.award_amount, award.currency)} {award.currency}
                      </div>
                      <div className="mt-1 text-xs text-[#6B7280]">{formatDate(award.award_date)}</div>
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

function IntelligenceSignals({ signals }: { signals: ProcurementIntelligenceSignal[] }) {
  if (signals.length === 0) {
    return <EmptyState message="No Phase 1 procurement intelligence signals were detected." />;
  }

  return (
    <div className="grid gap-3">
      {signals.map((signal) => (
        <div className="rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-4" key={`${signal.type}-${signal.company_id}-${signal.buyer}-${signal.score}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F]">
                <ShieldAlert className="h-4 w-4 text-[#D97706]" aria-hidden="true" />
                {signal.title}
              </div>
              <p className="mt-2 text-sm leading-6 text-[#4B5563]">{signal.summary}</p>
            </div>
            <span className="rounded-[12px] border border-[#D4A74B] bg-[#FFF5DD] px-2 py-1 text-xs font-semibold uppercase text-[#8A6412]">
              {signal.severity}
            </span>
          </div>
          <div className="mt-3 text-xs text-[#6B7280]">{signal.evidence.join(" | ")}</div>
        </div>
      ))}
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
