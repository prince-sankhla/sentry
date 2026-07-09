import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Building2, GitBranch, NotebookPen, ShieldAlert } from "lucide-react";

import { PageHeader, PageShell, SeverityBadge } from "@/components/ui/page";
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
import { formatDate, formatMoney, formatMoneyFull } from "@/lib/format";
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
          <div className="font-semibold text-text">{tender.title}</div>
          <div className="mt-1 font-mono text-xs text-faint">{tender.reference_number}</div>
        </div>
      )
    },
    {
      key: "buyer",
      header: "Buyer",
      render: (tender) => <span className="text-muted">{tender.buyer ?? "Unknown"}</span>
    },
    {
      key: "value",
      header: "Tender Value",
      sortHref: sortableHref("value"),
      align: "right",
      render: (tender) => (
        <span className="font-semibold tabular-nums text-text">
          {formatMoney(tender.tender_value, tender.currency)} {tender.currency}
        </span>
      )
    },
    {
      key: "published",
      header: "Published",
      sortHref: sortableHref("published_date"),
      render: (tender) => <span className="text-muted">{formatDate(tender.publication_date)}</span>
    },
    {
      key: "status",
      header: "Status",
      render: (tender) => <span className="text-muted">{tender.procurement_status ?? "Not stored"}</span>
    }
  ];

  return (
    <PageShell>
      <PageHeader
        eyebrow="Company File"
        title={overview.company.name}
        subtitle={
          <span className="font-mono text-faint">
            {overview.registration_identifier ?? "No registration identifier"}
          </span>
        }
        breadcrumb={[
          { label: "Dashboard", href: "/" },
          { label: "Company Investigation" }
        ]}
        actions={
          <Link
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong"
            href={`/graph?company_id=${companyId}&depth=2`}
          >
            <GitBranch className="h-4 w-4" aria-hidden="true" />
            Open graph
          </Link>
        }
      />

      <section className="grid w-full gap-5 xl:grid-cols-[360px_1fr]">
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
            <StatCard label="Procurement Value" value={formatMoneyFull(overview.total_procurement_value)} tone="warning" />
            <StatCard label="Average Award" value={formatMoneyFull(overview.average_award_value)} />
          </div>

          <SurfaceCard className="p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text">
              <NotebookPen className="h-4 w-4 text-accent" aria-hidden="true" />
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
              <div className="flex items-center gap-2 text-sm font-semibold text-text">
                <Building2 className="h-4 w-4 text-accent" aria-hidden="true" />
                Related Entities
              </div>
              <div className="mt-4">
                <EmptyState title="Graph-derived entities" message="Open the graph to inspect connected buyers, tenders, and awards." />
              </div>
            </SurfaceCard>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <Section eyebrow="Risk" title="Procurement Intelligence">
              <IntelligenceSignals signals={overview.intelligence.signals} />
            </Section>

            <Section eyebrow="Scoring" title="Buyer-Supplier Scores">
              {overview.intelligence.relationship_scores.length === 0 ? (
                <EmptyState message="No relationship score is available for this company." />
              ) : (
                <div className="space-y-3">
                  {overview.intelligence.relationship_scores.map((relationship) => (
                    <div className="rounded-[16px] border border-border bg-bg-2 p-3" key={`${relationship.buyer}-${relationship.supplier_id}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-text">{relationship.buyer ?? "Unknown buyer"}</div>
                          <div className="mt-1 text-xs text-muted">
                            {relationship.awards_to_supplier} of {relationship.total_buyer_awards} awards
                          </div>
                        </div>
                        <div className="text-lg font-semibold tabular-nums text-accent">{relationship.score}</div>
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
                  <div className="grid gap-3 rounded-[16px] border border-border bg-bg-2 p-4 transition hover:bg-surface-2 md:grid-cols-[1fr_auto]" key={award.id}>
                    <div>
                      <Link className="flex items-center gap-2 text-sm font-semibold text-text transition hover:text-accent" href={`/tenders/${award.tender_id}`}>
                        <Award className="h-4 w-4 text-accent" aria-hidden="true" />
                        {award.tender_title}
                      </Link>
                      <div className="mt-1 font-mono text-xs text-faint">{award.tender_reference_number}</div>
                    </div>
                    <div className="text-left md:text-right">
                      <div className="text-sm font-semibold tabular-nums text-text">
                        {formatMoney(award.award_amount, award.currency)} {award.currency}
                      </div>
                      <div className="mt-1 text-xs text-muted">{formatDate(award.award_date)}</div>
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
            <Section eyebrow="Evidence" title="Evidence Docket">
              <EvidenceDocket signals={overview.intelligence.signals} awards={awards.pagination.total} tenders={tenders.pagination.total} />
            </Section>
          </div>
        </div>
      </section>
    </PageShell>
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
    <div className="border-b border-border py-3 first:pt-0 last:border-b-0 last:pb-0">
      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-faint">{label}</div>
      <div className="mt-1 text-sm text-text">{value}</div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-border bg-bg-2 p-3">
      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-faint">{label}</div>
      <div className="mt-2 text-sm font-semibold text-text">{value}</div>
    </div>
  );
}

function IntelligenceSignals({ signals }: { signals: ProcurementIntelligenceSignal[] }) {
  if (signals.length === 0) {
    return <EmptyState message="No procurement intelligence signals were detected for this company." />;
  }

  return (
    <div className="grid gap-3">
      {signals.map((signal) => (
        <div className="rounded-[16px] border border-border bg-bg-2 p-4" key={`${signal.type}-${signal.company_id}-${signal.buyer}-${signal.score}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-text">
                <ShieldAlert className="h-4 w-4 text-accent" aria-hidden="true" />
                {signal.title}
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{signal.summary}</p>
            </div>
            <SeverityBadge severity={signal.severity} score={signal.score} />
          </div>
          {signal.evidence.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {signal.evidence.map((item, index) => (
                <span
                  className="rounded-md border border-border bg-bg-2 px-2 py-1 text-[11px] text-muted"
                  key={`${item}-${index}`}
                >
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function EvidenceDocket({
  signals,
  awards,
  tenders
}: {
  signals: ProcurementIntelligenceSignal[];
  awards: number;
  tenders: number;
}) {
  const evidenceItems = signals.flatMap((signal) => signal.evidence).slice(0, 6);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Signals" value={formatInteger(signals.length)} />
        <Metric label="Tenders" value={formatInteger(tenders)} />
        <Metric label="Awards" value={formatInteger(awards)} />
      </div>
      {evidenceItems.length === 0 ? (
        <EmptyState title="No cited evidence" message="The current company file has no extracted evidence references." />
      ) : (
        <ul className="space-y-2">
          {evidenceItems.map((item, index) => (
            <li className="rounded-[12px] border border-border bg-bg-2/40 p-3 text-sm text-muted" key={`${item}-${index}`}>
              {item}
            </li>
          ))}
        </ul>
      )}
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
