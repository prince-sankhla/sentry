"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Award,
  Check,
  Building2,
  Database,
  MapPin,
  FileText,
  Globe2,
  Landmark,
  Loader2,
  Clock3,
  Minus,
  Plus,
  RotateCcw,
  Search,
  Shield,
  Table2,
  Users
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";

import { RelationshipGraphExplorer } from "@/app/graph/relationship-graph";
import { Section, StatCard, SurfaceCard } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState, ErrorState, SkeletonBlock } from "@/components/ui/states";
import {
  getRelationshipGraph,
  getCompanies,
  getCanonicalCompany,
  getCompanyAwards,
  getCompanyOverview,
  getCompanyTenders,
  getDashboardRecent,
  getDashboardSummary,
  getProcurementEvidence,
  getTender,
  getTenders,
  searchWebEvidence,
  type CanonicalCompany,
  type CompanyAwardHistoryItem,
  type CompanyOverview,
  type CompanySearchSummary,
  type CompanyTenderHistoryItem,
  type DashboardRecent,
  type DashboardTender,
  type DashboardSummary,
  type ProcurementEvidence,
  type RelationshipGraph,
  type StoredWebPage,
  type TenderDetail,
  type TenderSummary,
  type WebSearchResult
} from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";

type StepStatus = "pending" | "running" | "complete" | "error";

type InvestigationStep = {
  name: string;
  status: StepStatus;
  startedAt?: number;
  finishedAt?: number;
  durationMs?: number;
  recordsFound?: number;
  detail?: string;
};

type InvestigationData = {
  query: string;
  scope: InvestigationScope;
  tenders: TenderSummary[];
  tenderDetails: TenderDetail[];
  companies: CompanySearchSummary[];
  companyOverviews: CompanyOverview[];
  companyTenderHistory: CompanyTenderHistoryItem[];
  companyAwardHistory: CompanyAwardHistoryItem[];
  canonicalCompanies: CanonicalCompany[];
  dashboardSummary: DashboardSummary | null;
  dashboardRecent: DashboardRecent | null;
  webResults: WebSearchResult[];
  webPages: StoredWebPage[];
  graph: RelationshipGraph | null;
  pagesDownloaded: number;
  duplicatesSkipped: number;
  totalTenders: number;
};

type InvestigationScope =
  | { kind: "company"; id: string; label: string }
  | { kind: "tender"; id: string; label: string }
  | { kind: "query"; label: string };

type CompanyProfileCard = {
  id: string;
  name: string;
  registration_number: string | null;
  href: string;
  awards: number;
  aliases?: string[];
  confidence?: string;
  sources?: number;
  procurementRecords?: number;
  webEvidence?: number;
};

const stepNames = [
  "Searching Procurement Sources",
  "Searching Web",
  "Downloading Evidence",
  "Extracting Information",
  "Building Investigation",
  "Completed"
];

const PAGE_SIZE = 5;

export function InvestigationWorkspace({ initialQuery }: { initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [steps, setSteps] = useState<InvestigationStep[]>(() => createSteps());
  const [data, setData] = useState<InvestigationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [homeRecent, setHomeRecent] = useState<DashboardRecent | null>(null);

  useEffect(() => {
    if (initialQuery) {
      runInvestigation(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  useEffect(() => {
    if (initialQuery) return;
    let cancelled = false;
    void getDashboardRecent(10)
      .then((recent) => {
        if (!cancelled) {
          setHomeRecent(recent);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHomeRecent(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialQuery]);

  async function runInvestigation(nextQuery: string) {
    const normalized = nextQuery.trim();
    if (!normalized) return;

    setActiveQuery(normalized);
    setQuery(normalized);
    setData(null);
    setError(null);
    setRunning(true);
    setSteps(createSteps());

    const investigation: InvestigationData = {
      query: normalized,
      scope: { kind: "query", label: normalized },
      tenders: [],
      tenderDetails: [],
      companies: [],
      companyOverviews: [],
      companyTenderHistory: [],
      companyAwardHistory: [],
      canonicalCompanies: [],
      dashboardSummary: null,
      dashboardRecent: null,
      webResults: [],
      webPages: [],
      graph: null,
      pagesDownloaded: 0,
      duplicatesSkipped: 0,
      totalTenders: 0
    };

    try {
      await runStep("Searching Procurement Sources", async () => {
        const [tenders, companies, dashboardSummary, dashboardRecent] = await Promise.all([
          getTenders({ q: normalized, limit: 25, sort: "newest" }),
          getCompanies({ q: normalized, limit: 10 }),
          getDashboardSummary().catch(() => null),
          getDashboardRecent(10).catch(() => null)
        ]);
        investigation.dashboardSummary = dashboardSummary;
        investigation.dashboardRecent = dashboardRecent;
        investigation.totalTenders = tenders.pagination.total;

        const primaryCompany = selectPrimaryCompany(companies.items, normalized);
        const primaryTender = selectPrimaryTender(tenders.items, normalized);

        if (primaryCompany) {
          investigation.scope = { kind: "company", id: primaryCompany.id, label: primaryCompany.name };
          investigation.companies = [primaryCompany];

          const [overview, companyTenders, awards, canonical] = await Promise.all([
            getCompanyOverview(primaryCompany.id).catch(() => null),
            getCompanyTenders(primaryCompany.id, { limit: 25 }).catch(() => null),
            getCompanyAwards(primaryCompany.id, 25).catch(() => null),
            getCanonicalCompany(primaryCompany.id).catch(() => null)
          ]);

          investigation.companyOverviews = overview ? [overview] : [];
          investigation.totalTenders = companyTenders?.pagination.total ?? investigation.totalTenders;
          const companyTenderHistory = companyTenders?.items ?? [];
          investigation.tenderDetails = await Promise.all(
            companyTenderHistory.slice(0, 8).map((tender) => getTender(tender.id).catch(() => null))
          ).then((items) => items.filter((item): item is TenderDetail => item !== null));
          investigation.tenders = investigation.tenderDetails.map(toTenderSummary);
          investigation.companyTenderHistory = companyTenderHistory;
          investigation.companyAwardHistory = awards?.items ?? [];
          investigation.canonicalCompanies = canonical ? [canonical] : [];
          return {
            recordsFound: (companyTenders?.pagination.total ?? 0) + (awards?.pagination.total ?? 0),
            detail: `${primaryCompany.name} company investigation loaded`
          };
        }

        if (primaryTender) {
          investigation.scope = { kind: "tender", id: primaryTender.id, label: primaryTender.title };
          investigation.tenders = [primaryTender];
          const tenderDetail = await getTender(primaryTender.id).catch(() => null);
          investigation.tenderDetails = tenderDetail ? [tenderDetail] : [];
          investigation.companies = companies.items.filter((item) => matchesQuery([item.name, item.registration_number ?? ""], normalized));
          investigation.companyOverviews = [];
          investigation.companyTenderHistory = [];
          investigation.companyAwardHistory = tenderDetail?.awards.map((award) => ({
            id: award.id,
            award_amount: award.award_value,
            award_date: award.award_date,
            currency: award.currency,
            tender_id: primaryTender.id,
            tender_title: primaryTender.title,
            tender_reference_number: primaryTender.reference_number
          })) ?? [];
          investigation.canonicalCompanies = [];
          return {
            recordsFound: tenderDetail ? tenderDetail.awards.length + 1 : 1,
            detail: `${primaryTender.title} tender investigation loaded`
          };
        }

        investigation.companies = companies.items.slice(0, 5);
        investigation.tenders = tenders.items.slice(0, 5);
        investigation.tenderDetails = await Promise.all(
          investigation.tenders.slice(0, 3).map((tender) => getTender(tender.id).catch(() => null))
        ).then((items) => items.filter((item): item is TenderDetail => item !== null));
        return {
          recordsFound: tenders.pagination.total + companies.pagination.total,
          detail: `${tenders.items.length} tenders and ${companies.items.length} companies loaded`
        };
      });

      await runStep("Searching Web", async () => {
        const web = await searchWebEvidence(normalized);
        const storedProcurement = await getProcurementEvidence(normalized).catch(() => ({ items: [] }));
        investigation.webResults = web.search_results;
        investigation.webPages = filterWebPages(
          mergeWebPages(web.stored_pages, storedProcurement.items),
          investigation.scope,
          normalized
        );
        investigation.pagesDownloaded = web.downloaded_pages;
        investigation.duplicatesSkipped = web.duplicates_skipped;
        return {
          recordsFound: web.search_results.length,
          detail: `${investigation.webPages.length} evidence pages available`
        };
      });

      await runStep("Downloading Evidence", async () => ({
        recordsFound: investigation.pagesDownloaded,
        detail: `${investigation.duplicatesSkipped} duplicate pages skipped`
      }));

      await runStep("Extracting Information", async () => ({
        recordsFound: procurementEvidenceRows(investigation.webPages).length,
        detail: "Procurement evidence extracted by Web Intelligence"
      }));

      await runStep("Building Investigation", async () => {
        const evidence = procurementEvidenceRows(investigation.webPages);
        const primaryCompanyId = investigation.scope.kind === "company" ? investigation.scope.id : evidence.find((item) => item.company_id)?.company_id ?? undefined;
        const primaryTenderId = investigation.scope.kind === "tender" ? investigation.scope.id : investigation.tenders[0]?.id ?? evidence.find((item) => item.tender_id)?.tender_id ?? undefined;

        investigation.graph = primaryCompanyId
          ? await getRelationshipGraph({ companyId: primaryCompanyId, depth: 2 }).catch(() => null)
          : primaryTenderId
            ? await getRelationshipGraph({ tenderId: primaryTenderId, depth: 2 }).catch(() => null)
            : null;
        return {
          recordsFound: (investigation.graph?.nodes.length ?? 0) + (investigation.graph?.edges.length ?? 0),
          detail: investigation.graph ? "Investigation graph loaded" : "Graph unavailable"
        };
      });

      await runStep("Completed", async () => ({
        recordsFound: investigation.totalTenders + investigation.webPages.length,
        detail: "Investigation workspace ready"
      }));

      setData(investigation);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Investigation failed");
      setSteps((current) =>
        current.map((step) => (step.status === "running" ? { ...step, status: "error", finishedAt: performance.now() } : step))
      );
    } finally {
      setRunning(false);
    }
  }

  async function runStep(
    name: string,
    action: () => Promise<{ recordsFound?: number; detail?: string }>
  ) {
    const startedAt = performance.now();
    setSteps((current) =>
      current.map((step) => (step.name === name ? { ...step, status: "running", startedAt } : step))
    );
    const result = await action();
    const finishedAt = performance.now();
    setSteps((current) =>
      current.map((step) =>
        step.name === name
          ? {
              ...step,
              status: "complete",
              finishedAt,
              durationMs: Math.round(finishedAt - startedAt),
              recordsFound: result.recordsFound,
              detail: result.detail
            }
          : step
      )
    );
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runInvestigation(query);
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-bg text-text">
      <section className="border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto w-full max-w-[1600px] px-6 py-6 lg:px-8">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-[#B88927]">
                <Shield className="h-4 w-4" aria-hidden="true" />
                Investigation Workspace
                <span className="rounded-full border border-border bg-[#FBF7F0] px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-[#6B7280]">
                  {running ? "Running" : data ? "Completed" : "Ready"}
                </span>
              </div>
              <div className="mt-3 flex flex-col gap-4">
                <h1 className="text-4xl font-semibold tracking-tight text-[#2F2F2F] sm:text-5xl">
                  Investigation: {activeQuery || "Start a new procurement search"}
                </h1>
                <p className="max-w-4xl text-sm leading-6 text-[#6B7280]">
                  A procurement-only workspace that layers investigation steps, evidence, relationships, and geographic context from the existing APIs.
                </p>
                <form className="flex flex-col gap-3 sm:flex-row" onSubmit={onSubmit}>
                  <label className="relative flex-1">
                    <span className="sr-only">Investigation search query</span>
                    <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6B7280]" />
                    <input
                      className="h-12 w-full rounded-[18px] border border-[#E8D8B1] bg-white pl-11 pr-4 text-sm text-[#2F2F2F] outline-none placeholder:text-[#8C919A] focus:border-[#D4A74B]"
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Reliance Jio, TCS, Infosys, Adani"
                      type="search"
                      value={query}
                    />
                  </label>
                  <button
                    className="inline-flex h-12 items-center justify-center gap-2 rounded-[18px] border border-[#D4A74B] bg-[#FFF5DD] px-5 text-sm font-semibold text-[#8A6412] transition hover:bg-[#F9E7B8] disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={running}
                    type="submit"
                  >
                    {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                    Start Investigation
                  </button>
                </form>
              </div>
            </div>
            <div className="flex shrink-0 items-start gap-3">
              <Link
                className="inline-flex h-12 items-center justify-center rounded-[18px] border border-[#E8D8B1] bg-white px-4 text-sm font-semibold text-[#2F2F2F] transition hover:border-[#D4A74B] hover:shadow-[0_18px_40px_rgba(87,63,14,0.08)]"
                href="/"
              >
                New Investigation
              </Link>
            </div>
          </div>
          <div className="mt-6">
            <PipelineStrip items={steps} />
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-[1600px] px-6 py-6 lg:px-8">
        {error ? <ErrorState title="Investigation failed" message={error} /> : null}
        {!activeQuery && !data && !running ? <StartState /> : null}
        {running && !data ? <LoadingWorkspace /> : null}
        {data ? <InvestigationDashboard data={data} steps={steps} /> : null}
      </section>
    </main>
  );
}

function InvestigationDashboard({ data, steps }: { data: InvestigationData; steps: InvestigationStep[] }) {
  const awards = useMemo(
    () => data.tenderDetails.flatMap((tender) => tender.awards.map((award) => ({ ...award, tender }))),
    [data.tenderDetails]
  );
  const procurementEvidence = useMemo(() => procurementEvidenceRows(data.webPages), [data.webPages]);
  const buyers = useMemo(() => buyerRows(data.tenders, procurementEvidence), [data.tenders, procurementEvidence]);
  const relatedCompanies = useMemo(() => {
    const companies = new Map<string, { id: string; name: string; registration_number: string | null; awards: number }>();
    for (const award of awards) {
      const current = companies.get(award.company.id);
      companies.set(award.company.id, {
        id: award.company.id,
        name: award.company.name,
        registration_number: award.company.registration_number,
        awards: (current?.awards ?? 0) + 1
      });
    }
    for (const company of data.companies) {
      const current = companies.get(company.id);
      companies.set(company.id, {
        id: company.id,
        name: company.name,
        registration_number: company.registration_number,
        awards: current?.awards ?? 0
      });
    }
    return [...companies.values()].sort((left, right) => right.awards - left.awards || left.name.localeCompare(right.name));
  }, [awards, data.companies]);
  const companyProfiles = useMemo<CompanyProfileCard[]>(() => {
    if (data.canonicalCompanies.length > 0) {
      return data.canonicalCompanies.map((company) => ({
        id: company.id,
        name: company.canonical_name,
        registration_number: company.linked_procurement_companies[0]?.registration_number ?? null,
        href: `/companies/${company.linked_procurement_companies[0]?.id ?? company.linked_company_ids[0] ?? company.id}`,
        awards: company.linked_awards.length,
        aliases: company.aliases,
        confidence: company.confidence,
        sources: company.matched_sources.length,
        procurementRecords: company.linked_procurement_companies.length,
        webEvidence: company.linked_web_evidence.length
      }));
    }
    return relatedCompanies.slice(0, 3).map((company) => ({ ...company, href: `/companies/${company.id}` }));
  }, [data.canonicalCompanies, relatedCompanies]);
  const sources = useMemo(() => sourceRows(data.webResults, data.webPages, steps), [data.webResults, data.webPages, steps]);
  const categories = useMemo(() => countValues(procurementEvidence.map((item) => item.procurement_sector ?? item.tender_category)), [procurementEvidence]);
  const countries = useMemo(() => countValues(procurementEvidence.map((item) => item.country)), [procurementEvidence]);
  const timelineItems = useMemo(() => buildInvestigationTimeline(data, awards, procurementEvidence), [awards, data, procurementEvidence]);
  const totalValue = sumMoney(data.tenders.map((tender) => tender.estimated_value));
  const procurementGraph = useMemo(() => buildProcurementGraph(data.graph), [data.graph]);
  const locationClusters = useMemo(
    () => buildLocationClusters(data, procurementEvidence),
    [data, procurementEvidence]
  );
  const primaryBuyer = buyers[0]?.name ?? "Not available";
  const procurementAvailable = data.tenders.length > 0 || awards.length > 0 || procurementEvidence.length > 0;

  return (
    <div className="space-y-6 pb-8">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Total Tenders" tone="accent" value={formatInteger(data.totalTenders)} meta={data.scope.label} />
        <StatCard label="Total Awards" tone="success" value={formatInteger(awards.length)} meta="Awards indexed from tender detail responses" />
        <StatCard label="Companies" value={formatInteger(relatedCompanies.length || data.companies.length || data.canonicalCompanies.length)} meta="Connected procurement entities" />
        <StatCard label="Web Evidence" value={formatInteger(data.webPages.length)} meta={`${data.duplicatesSkipped} duplicates skipped`} />
        <StatCard label="Procurement Value" tone="warning" value={totalValue === null ? "Not disclosed" : formatMoney(String(totalValue), data.tenders[0]?.currency ?? "INR")} meta="From disclosed tender and award values" />
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,7fr)_minmax(0,3fr)]">
        <div className="min-w-0 space-y-5">
          <Section eyebrow="Pipeline" title="Investigation Timeline">
            <TimelineStrip items={timelineItems} />
          </Section>

          <Section
            eyebrow="Evidence"
            title="Procurement Evidence Table"
            action={<PaginationSummary pageIndex={0} pageSize={PAGE_SIZE} total={procurementEvidence.length} />}
          >
            <ProcurementEvidenceTable evidence={procurementEvidence} pages={data.webPages} />
          </Section>

          <Section eyebrow="Geography" title="Geographic Map">
            <ProcurementMap clusters={locationClusters} />
          </Section>

          <Section eyebrow="History" title="Tender History">
            {data.tenders.length === 0 ? (
              <EmptyState title="No procurement records found" message="No tenders were returned for this investigation." />
            ) : (
              <TenderHistoryTable tenders={data.tenders} />
            )}
          </Section>

          <Section eyebrow="History" title="Award History">
            {awards.length === 0 ? (
              <EmptyState title="No procurement records found" message="No awards were returned for this investigation." />
            ) : (
              <AwardHistoryTable awards={awards} />
            )}
          </Section>
        </div>

        <div className="min-w-0 space-y-5">
          <Section eyebrow="Overview" title="Procurement Overview">
            {procurementAvailable ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <OverviewTile label="Scope" value={data.scope.kind === "company" ? "Company investigation" : data.scope.kind === "tender" ? "Tender investigation" : "Query investigation"} />
                <OverviewTile label="Top buyer" value={primaryBuyer} />
                <OverviewTile label="Procurement records" value={formatInteger(procurementEvidence.length)} />
                <OverviewTile label="Countries" value={countries.length ? countries.map((item) => `${item.name} (${item.count})`).join(", ") : "India"} />
                <OverviewTile label="Categories" value={categories.length ? categories.slice(0, 3).map((item) => item.name).join(", ") : "Not available"} />
              </div>
            ) : (
              <EmptyState title="No procurement records found" message="No tenders, awards, or procurement evidence were returned for the connected procurement sources." />
            )}
          </Section>

          <Section eyebrow="Graph" title="Relationship Graph">
            {procurementGraph.nodes.length > 0 ? (
              <div className="overflow-hidden rounded-[24px] border border-[#E8D8B1] bg-white">
                <RelationshipGraphExplorer graph={procurementGraph} />
              </div>
            ) : (
              <EmptyState title="No procurement records found" message="The existing graph API did not return procurement-related relationships for this investigation." />
            )}
          </Section>

          <Section eyebrow="Buyers" title="Government Buyers">
            {buyers.length === 0 ? <EmptyState title="No procurement records found" message="No buyers were extracted from the procurement evidence." /> : <GovernmentBuyersTable buyers={buyers} />}
          </Section>

          <Section eyebrow="Network" title="Connected Companies">
            {companyProfiles.length === 0 ? (
              <EmptyState title="No procurement records found" message="No connected companies were resolved from the current procurement record set." />
            ) : (
              <ConnectedCompaniesPanel companies={companyProfiles} />
            )}
          </Section>

          <Section eyebrow="Documents" title="Documents">
            {data.webPages.length === 0 ? (
              <EmptyState title="No procurement records found" message="No procurement documents were stored for this investigation." />
            ) : (
              <DocumentsTable pages={data.webPages} />
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}

function PipelineStrip({ items }: { items: InvestigationStep[] }) {
  return (
    <div className="grid gap-3 xl:grid-cols-6">
      {items.map((item, index) => (
        <div className="rounded-[18px] border border-[#E8D8B1] bg-[#FFFDF8] p-4 shadow-[0_14px_36px_rgba(87,63,14,0.05)]" key={item.name}>
          <div className="flex items-center gap-2">
            <PipelineDot status={item.status} />
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#B88927]">Step {index + 1}</div>
          </div>
          <div className="mt-3 text-sm font-semibold leading-5 text-[#2F2F2F]">{pipelineStepLabel(item.name)}</div>
          <div className="mt-1 text-xs text-[#6B7280]">{item.detail ?? pipelineStepDetail(item.name)}</div>
        </div>
      ))}
    </div>
  );
}

function PipelineDot({ status }: { status: StepStatus }) {
  if (status === "complete") {
    return <Check className="h-4 w-4 text-[#8DA175]" aria-hidden="true" />;
  }
  if (status === "running") {
    return <Loader2 className="h-4 w-4 animate-spin text-[#B88927]" aria-hidden="true" />;
  }
  if (status === "error") {
    return <span className="h-4 w-4 rounded-full border border-[#C97A7A] bg-[#FFF0F0]" aria-hidden="true" />;
  }
  return <span className="h-4 w-4 rounded-full border border-[#E2C67E] bg-white" aria-hidden="true" />;
}

function TimelineStrip({ items }: { items: TimelineItem[] }) {
  if (items.length === 0) {
    return <EmptyState title="No timeline events available" message="No investigation timeline events were available for the active query." />;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div className="rounded-[18px] border border-[#E8D8B1] bg-white p-4 shadow-[0_14px_36px_rgba(87,63,14,0.05)]" key={`${item.label}-${item.value}`}>
          <div className="flex items-start gap-2 text-sm font-semibold text-[#2F2F2F]">
            <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-[#B88927]" aria-hidden="true" />
            <span className="min-w-0 break-words leading-5">{item.label}</span>
          </div>
          <div className="mt-3 text-xs uppercase tracking-[0.12em] text-[#7A7F87]">Value</div>
          <div className="mt-1 break-words text-sm font-semibold text-[#2F2F2F]">{item.value}</div>
          <div className="mt-3 break-words text-xs leading-5 text-[#6B7280]">{item.detail ?? "Not available"}</div>
        </div>
      ))}
    </div>
  );
}

function OverviewTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[18px] border border-[#E8D8B1] bg-[#FFFDF8] p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#7A7F87]">{label}</div>
      <div className="mt-2 break-words text-sm font-semibold leading-5 text-[#2F2F2F]">{value}</div>
    </div>
  );
}

function ProcurementEvidenceTable({ evidence, pages }: { evidence: ProcurementEvidence[]; pages: StoredWebPage[] }) {
  const [filter, setFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const pageByEvidenceId = new Map(pages.map((page) => [page.procurement_evidence?.id, page]));
  const items = useMemo(
    () => filterItems(evidence, filter, (item) => `${item.company_name ?? ""} ${item.government_buyer ?? ""} ${item.tender_title ?? ""} ${item.contract_title ?? ""} ${item.country ?? ""}`),
    [evidence, filter]
  );
  const visible = paginateItems(items, pageIndex, PAGE_SIZE);
  useEffect(() => setPageIndex(0), [filter, evidence.length]);
  const columns: Column<ProcurementEvidence>[] = [
    { key: "company", header: "Company", render: (item) => <RecordTitle title={item.company_name ?? item.normalized_company_name ?? "Unknown company"} meta={item.organization ?? "Extracted from web evidence"} /> },
    { key: "buyer", header: "Government Buyer", render: (item) => <span>{item.government_buyer ?? "Not available"}</span> },
    { key: "procurement", header: "Procurement", render: (item) => <RecordTitle title={item.tender_title ?? item.contract_title ?? "Untitled procurement evidence"} meta={item.tender_number ?? item.contract_number ?? item.procurement_sector ?? "No reference number"} /> },
    { key: "value", header: "Value", align: "right", render: (item) => <span>{item.contract_value ? formatMoney(item.contract_value, item.currency ?? "") : "Not disclosed"}</span> },
    { key: "source", header: "Source", render: (item) => {
      const page = pageByEvidenceId.get(item.id);
      return page ? <a className="break-all text-[#B88927] hover:underline" href={page.url} rel="noreferrer" target="_blank">{page.source}</a> : <span>Stored evidence</span>;
    } }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <TableFilter value={filter} onChange={setFilter} placeholder="Search evidence" />
        <PaginationSummary pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} />
      </div>
      <DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No procurement facts were extracted from web evidence." />} items={visible} />
      <PaginationBar pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} onNext={() => setPageIndex((value) => Math.min(value + 1, Math.max(0, Math.ceil(items.length / PAGE_SIZE) - 1)))} onPrev={() => setPageIndex((value) => Math.max(0, value - 1))} />
    </div>
  );
}

function TenderHistoryTable({ tenders }: { tenders: TenderSummary[] }) {
  const [filter, setFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const items = useMemo(
    () => filterItems(tenders, filter, (tender) => `${tender.title} ${tender.reference_number} ${tender.procuring_entity ?? ""}`),
    [filter, tenders]
  );
  const visible = paginateItems(items, pageIndex, PAGE_SIZE);
  useEffect(() => setPageIndex(0), [filter, tenders.length]);
  const columns: Column<TenderSummary>[] = [
    { key: "title", header: "Tender", render: (tender) => <RecordTitle title={tender.title} meta={tender.reference_number} /> },
    { key: "buyer", header: "Buyer", render: (tender) => <span>{tender.procuring_entity ?? "Unknown"}</span> },
    { key: "value", header: "Value", align: "right", render: (tender) => <span>{formatMoney(tender.estimated_value, tender.currency)}</span> },
    { key: "published", header: "Published", render: (tender) => <span>{formatDate(tender.published_date)}</span> }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <TableFilter value={filter} onChange={setFilter} placeholder="Search tenders" />
        <PaginationSummary pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} />
      </div>
      <DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No tenders match this investigation." />} getHref={(tender) => `/tenders/${tender.id}`} items={visible} />
      <PaginationBar pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} onNext={() => setPageIndex((value) => Math.min(value + 1, Math.max(0, Math.ceil(items.length / PAGE_SIZE) - 1)))} onPrev={() => setPageIndex((value) => Math.max(0, value - 1))} />
    </div>
  );
}

function AwardHistoryTable({ awards }: { awards: Array<TenderDetail["awards"][number] & { tender: TenderDetail }> }) {
  const [filter, setFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const items = useMemo(
    () => filterItems(awards, filter, (award) => `${award.company.name} ${award.tender.title} ${award.currency}`),
    [awards, filter]
  );
  const visible = paginateItems(items, pageIndex, PAGE_SIZE);
  useEffect(() => setPageIndex(0), [filter, awards.length]);
  const columns: Column<(typeof awards)[number]>[] = [
    { key: "company", header: "Company", render: (award) => <RecordTitle title={award.company.name} meta={award.company.registration_number ?? "No identifier"} /> },
    { key: "tender", header: "Tender", render: (award) => <span>{award.tender.title}</span> },
    { key: "amount", header: "Award Value", align: "right", render: (award) => <span>{formatMoney(award.award_value, award.currency)}</span> },
    { key: "date", header: "Award Date", render: (award) => <span>{formatDate(award.award_date)}</span> }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <TableFilter value={filter} onChange={setFilter} placeholder="Search awards" />
        <PaginationSummary pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} />
      </div>
      <DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No award history is available from tender details." />} items={visible} />
      <PaginationBar pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} onNext={() => setPageIndex((value) => Math.min(value + 1, Math.max(0, Math.ceil(items.length / PAGE_SIZE) - 1)))} onPrev={() => setPageIndex((value) => Math.max(0, value - 1))} />
    </div>
  );
}

function GovernmentBuyersTable({ buyers }: { buyers: Array<{ id: string; name: string; records: number }> }) {
  const [filter, setFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const items = useMemo(() => filterItems(buyers, filter, (buyer) => buyer.name), [buyers, filter]);
  const visible = paginateItems(items, pageIndex, PAGE_SIZE);
  useEffect(() => setPageIndex(0), [buyers.length, filter]);
  const columns: Column<(typeof buyers)[number]>[] = [
    { key: "buyer", header: "Government Buyer", render: (buyer) => <span className="font-semibold text-[#2F2F2F]">{buyer.name}</span> },
    { key: "records", header: "Records", align: "right", render: (buyer) => <span>{buyer.records}</span> },
    { key: "documents", header: "Documents", render: () => <span>Linked procurement evidence</span> }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <TableFilter value={filter} onChange={setFilter} placeholder="Search buyers" />
        <PaginationSummary pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} />
      </div>
      <DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No government buyers were returned by procurement records." />} items={visible} />
      <PaginationBar pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} onNext={() => setPageIndex((value) => Math.min(value + 1, Math.max(0, Math.ceil(items.length / PAGE_SIZE) - 1)))} onPrev={() => setPageIndex((value) => Math.max(0, value - 1))} />
    </div>
  );
}

function ConnectedCompaniesPanel({ companies }: { companies: CompanyProfileCard[] }) {
  return (
    <div className="grid gap-3">
      {companies.map((company) => (
        <Link className="rounded-[18px] border border-[#E8D8B1] bg-[#FFFDF8] p-4 transition hover:border-[#D4A74B] hover:shadow-[0_18px_42px_rgba(87,63,14,0.08)]" href={company.href} key={company.id}>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm font-semibold leading-5 text-[#2F2F2F]">{company.name}</div>
              <div className="mt-1 break-words text-xs text-[#6B7280]">{company.registration_number ?? "No identifier"}</div>
            </div>
            <Building2 className="h-4 w-4 shrink-0 text-[#B88927]" aria-hidden="true" />
          </div>
          <div className="mt-3 grid gap-2 text-xs text-[#6B7280] sm:grid-cols-2">
            <MiniFact label="Awards" value={String(company.awards)} />
            <MiniFact label="Sources" value={String(company.sources ?? 0)} />
            <MiniFact label="Procurement" value={String(company.procurementRecords ?? 0)} />
            <MiniFact label="Web evidence" value={String(company.webEvidence ?? 0)} />
          </div>
          {company.aliases && company.aliases.length > 0 ? <div className="mt-3 text-xs leading-5 text-[#6B7280]">Aliases: {company.aliases.join(", ")}</div> : null}
        </Link>
      ))}
    </div>
  );
}

function DocumentsTable({ pages }: { pages: StoredWebPage[] }) {
  const [filter, setFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const items = useMemo(() => filterItems(pages, filter, (page) => `${page.title ?? ""} ${page.source} ${page.url}`), [pages, filter]);
  const visible = paginateItems(items, pageIndex, PAGE_SIZE);
  useEffect(() => setPageIndex(0), [filter, pages.length]);
  const columns: Column<StoredWebPage>[] = [
    { key: "source", header: "Source", render: (page) => <RecordTitle title={page.title ?? page.source} meta={page.source} /> },
    { key: "url", header: "URL", render: (page) => <a className="break-all text-[#B88927] hover:underline" href={page.url} rel="noreferrer" target="_blank">{page.url}</a> },
    { key: "retrieved", header: "Retrieved", render: (page) => <span>{formatDate(page.retrieved_at)}</span> },
    { key: "entities", header: "Entities", align: "right", render: (page) => <span>{page.extraction.organization_names.length}</span> }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <TableFilter value={filter} onChange={setFilter} placeholder="Search documents" />
        <PaginationSummary pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} />
      </div>
      <DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No documents were stored for this investigation." />} items={visible} />
      <PaginationBar pageIndex={pageIndex} pageSize={PAGE_SIZE} total={items.length} onNext={() => setPageIndex((value) => Math.min(value + 1, Math.max(0, Math.ceil(items.length / PAGE_SIZE) - 1)))} onPrev={() => setPageIndex((value) => Math.max(0, value - 1))} />
    </div>
  );
}

function ProcurementMap({ clusters }: { clusters: LocationCluster[] }) {
  const [zoom, setZoom] = useState(1);
  const [activeClusterId, setActiveClusterId] = useState<string | null>(clusters[0]?.id ?? null);
  const activeCluster = clusters.find((cluster) => cluster.id === activeClusterId) ?? clusters[0] ?? null;
  const zoomClass = mapZoomClass(zoom);

  useEffect(() => {
    setActiveClusterId(clusters[0]?.id ?? null);
  }, [clusters]);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
      <div className="relative overflow-hidden rounded-[24px] border border-[#E8D8B1] bg-gradient-to-br from-[#FFFDF8] to-[#F6EDD7] p-4 shadow-[0_20px_48px_rgba(87,63,14,0.08)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(212,167,75,0.12),transparent_30%),radial-gradient(circle_at_70%_30%,rgba(212,167,75,0.08),transparent_28%),radial-gradient(circle_at_50%_80%,rgba(212,167,75,0.08),transparent_24%)]" />
        <div className="relative flex items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#B88927]">India Procurement Map</div>
            <div className="mt-1 text-sm text-[#6B7280]">Clusters are derived only from procurement evidence text and company/overview addresses.</div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-[#E8D8B1] bg-white p-1">
            <MapButton icon={<Minus className="h-3.5 w-3.5" />} onClick={() => setZoom((value) => Math.max(0.8, Number((value - 0.1).toFixed(2))))} label="Zoom out" />
            <MapButton icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setZoom((value) => Math.min(1.5, Number((value + 0.1).toFixed(2))))} label="Zoom in" />
            <MapButton icon={<RotateCcw className="h-3.5 w-3.5" />} onClick={() => setZoom(1)} label="Reset" />
          </div>
        </div>

        <div className="relative mt-4 aspect-[1.6] overflow-hidden rounded-[24px] border border-[#E8D8B1] bg-[#FCF8EF]">
          <div className="absolute inset-0 opacity-70">
            <svg className="h-full w-full" preserveAspectRatio="none" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="india-map-fill" x1="0" x2="1" y1="0" y2="1">
                  <stop offset="0%" stopColor="#F7E7B5" />
                  <stop offset="100%" stopColor="#E9C873" />
                </linearGradient>
              </defs>
              <path d="M46 6 L58 10 L67 18 L73 27 L77 38 L76 49 L71 59 L67 69 L60 78 L53 89 L45 85 L40 74 L34 65 L27 56 L21 45 L23 33 L29 23 L36 14 Z" fill="url(#india-map-fill)" opacity="0.38" stroke="#D4A74B" strokeWidth="0.7" />
              <path d="M47 17 L54 19 L59 28 L57 38 L52 47 L48 58 L41 68 L36 61 L33 50 L35 39 L40 29 Z" fill="none" stroke="#D4A74B" strokeDasharray="1.5 1.5" strokeWidth="0.4" opacity="0.55" />
              <path d="M30 41 L40 44 L50 44 L61 47 L69 55" fill="none" stroke="#D4A74B" strokeWidth="0.3" opacity="0.45" />
            </svg>
          </div>
          <div className="absolute inset-0 grid grid-cols-6 grid-rows-6 opacity-[0.08]">
            {Array.from({ length: 36 }).map((_, index) => <div className="border-l border-t border-[#B88927]" key={index} />)}
          </div>
          <div className="relative h-full w-full">
            <div className={`absolute left-1/2 top-1/2 h-[72%] w-[72%] -translate-x-1/2 -translate-y-1/2 ${zoomClass}`}>
              {clusters.map((cluster) => (
                <button
                  key={cluster.id}
                  onClick={() => setActiveClusterId(cluster.id)}
                  className={`absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-sm transition ${cluster.positionClass} ${
                    cluster.id === activeCluster?.id ? "border-[#B88927] bg-white text-[#2F2F2F]" : "border-[#E8D8B1] bg-white/90 text-[#6B7280] hover:border-[#D4A74B]"
                  }`}
                  type="button"
                >
                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#FFF5DD] text-[#B88927]">
                    <MapPin className="h-3 w-3" aria-hidden="true" />
                  </span>
                  <span>{cluster.count}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <aside className="space-y-3 rounded-[24px] border border-[#E8D8B1] bg-[#FFFDF8] p-4">
        <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#B88927]">Location clusters</div>
        <div className="space-y-2">
          {clusters.length === 0 ? (
            <EmptyState title="No procurement records found" message="No geographic hints were extracted from the current evidence set." />
          ) : (
            clusters.map((cluster) => (
              <button
                className={`w-full rounded-[16px] border px-3 py-3 text-left transition ${cluster.id === activeCluster?.id ? "border-[#B88927] bg-white" : "border-[#E8D8B1] bg-white/70 hover:border-[#D4A74B]"}`}
                key={cluster.id}
                onClick={() => setActiveClusterId(cluster.id)}
                type="button"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-[#2F2F2F]">{cluster.label}</div>
                  <div className="rounded-full bg-[#FFF5DD] px-2 py-1 text-xs font-semibold text-[#8A6412]">{cluster.count}</div>
                </div>
                <div className="mt-1 text-xs text-[#6B7280]">{cluster.detail}</div>
              </button>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}

function MapButton({ icon, label, onClick }: { icon: ReactNode; label: string; onClick: () => void }) {
  return (
    <button className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[#E8D8B1] text-[#6B7280] transition hover:border-[#D4A74B] hover:text-[#2F2F2F]" onClick={onClick} type="button" aria-label={label}>
      {icon}
    </button>
  );
}

function mapZoomClass(zoom: number): string {
  if (zoom <= 0.85) return "scale-[0.85]";
  if (zoom <= 0.95) return "scale-90";
  if (zoom <= 1.05) return "scale-100";
  if (zoom <= 1.15) return "scale-110";
  return "scale-125";
}

function TableFilter({ value, onChange, placeholder, readOnly = false }: { value: string; onChange: (value: string) => void; placeholder: string; readOnly?: boolean }) {
  return (
    <label className="relative block">
      <span className="sr-only">{placeholder}</span>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#7A7F87]" aria-hidden="true" />
      <input
        className="h-10 w-full rounded-[14px] border border-[#E8D8B1] bg-white pl-9 pr-3 text-sm text-[#2F2F2F] outline-none placeholder:text-[#8C919A] focus:border-[#D4A74B]"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        readOnly={readOnly}
        value={value}
      />
    </label>
  );
}

function PaginationSummary({ pageIndex, pageSize, total }: { pageIndex: number; pageSize: number; total: number }) {
  const start = total === 0 ? 0 : pageIndex * pageSize + 1;
  const end = Math.min(total, (pageIndex + 1) * pageSize);
  return <div className="text-xs text-[#6B7280]">Showing {start} to {end} of {total}</div>;
}

function PaginationBar({ pageIndex, pageSize, total, onPrev, onNext }: { pageIndex: number; pageSize: number; total: number; onPrev: () => void; onNext: () => void }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between gap-3 rounded-[18px] border border-[#E8D8B1] bg-[#FFFDF8] px-4 py-3 text-xs text-[#6B7280]">
      <span>
        Page {total === 0 ? 0 : pageIndex + 1} of {totalPages}
      </span>
      <div className="flex items-center gap-2">
        <button className="rounded-full border border-[#E8D8B1] px-3 py-1.5 font-semibold text-[#2F2F2F] disabled:opacity-40" disabled={pageIndex === 0 || total === 0} onClick={onPrev} type="button">
          Previous
        </button>
        <button className="rounded-full border border-[#E8D8B1] px-3 py-1.5 font-semibold text-[#2F2F2F] disabled:opacity-40" disabled={pageIndex >= totalPages - 1 || total === 0} onClick={onNext} type="button">
          Next
        </button>
      </div>
    </div>
  );
}

function MiniFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[14px] border border-[#E8D8B1] bg-white px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7A7F87]">{label}</div>
      <div className="mt-1 break-words text-xs font-semibold text-[#2F2F2F]">{value}</div>
    </div>
  );
}

function paginateItems<T>(items: T[], pageIndex: number, pageSize: number): T[] {
  return items.slice(pageIndex * pageSize, pageIndex * pageSize + pageSize);
}

function pipelineStepLabel(name: string): string {
  if (name === "Searching Procurement Sources") return "Searching Procurement";
  if (name === "Building Investigation") return "Building Graph";
  return name;
}

function pipelineStepDetail(name: string): string {
  if (name === "Searching Procurement Sources") return "Loading tenders, companies, and dashboard summaries";
  if (name === "Searching Web") return "Downloading only procurement-related web evidence";
  if (name === "Downloading Evidence") return "Skipping duplicate pages and storing new evidence";
  if (name === "Extracting Information") return "Extracting procurement facts from stored evidence";
  if (name === "Building Investigation") return "Building a procurement-only relationship graph";
  return "Investigation workspace ready";
}

type LocationCluster = {
  id: string;
  label: string;
  detail: string;
  count: number;
  positionClass: string;
};

const INDIA_LOCATION_POINTS: Array<{ id: string; label: string; terms: string[]; positionClass: string }> = [
  { id: "delhi", label: "Delhi NCR", terms: ["delhi", "new delhi", "gurgaon", "noida", "ghaziabad"], positionClass: "left-[53%] top-[20%]" },
  { id: "chandigarh", label: "Chandigarh / Punjab", terms: ["chandigarh", "punjab"], positionClass: "left-[41%] top-[15%]" },
  { id: "ahmedabad", label: "Ahmedabad / Gujarat", terms: ["ahmedabad", "gujarat"], positionClass: "left-[28%] top-[38%]" },
  { id: "mumbai", label: "Mumbai / Maharashtra", terms: ["mumbai", "maharashtra", "pune"], positionClass: "left-[34%] top-[53%]" },
  { id: "hyderabad", label: "Hyderabad / Telangana", terms: ["hyderabad", "telangana"], positionClass: "left-[54%] top-[66%]" },
  { id: "bengaluru", label: "Bengaluru / Karnataka", terms: ["bengaluru", "bangalore", "karnataka"], positionClass: "left-[50%] top-[78%]" },
  { id: "chennai", label: "Chennai / Tamil Nadu", terms: ["chennai", "tamil nadu"], positionClass: "left-[62%] top-[87%]" },
  { id: "kochi", label: "Kochi / Kerala", terms: ["kochi", "kerala"], positionClass: "left-[55%] top-[94%]" },
  { id: "kolkata", label: "Kolkata / West Bengal", terms: ["kolkata", "west bengal"], positionClass: "left-[81%] top-[53%]" },
  { id: "bhubaneswar", label: "Bhubaneswar / Odisha", terms: ["bhubaneswar", "odisha"], positionClass: "left-[76%] top-[63%]" }
];

function buildLocationClusters(data: InvestigationData, evidence: ProcurementEvidence[]): LocationCluster[] {
  const clusters = new Map<string, LocationCluster>();
  const sources = [
    data.scope.label,
    ...data.companyOverviews.map((overview) => [overview.address, overview.company.address].filter(Boolean).join(" ")),
    ...evidence.flatMap((item) => [item.company_name, item.government_buyer, item.tender_title, item.contract_title, item.organization, item.country].filter(Boolean) as string[])
  ];

  for (const source of sources) {
    const normalized = source.toLowerCase();
    let matchedPoint = INDIA_LOCATION_POINTS.find((point) => point.terms.some((term) => normalized.includes(term)));
    if (!matchedPoint && normalized.includes("india")) {
      matchedPoint = { id: "india", label: "India", terms: ["india"], positionClass: "left-[55%] top-[52%]" };
    }
    if (!matchedPoint) continue;

    const current = clusters.get(matchedPoint.id) ?? {
      id: matchedPoint.id,
      label: matchedPoint.label,
      detail: "Derived from procurement evidence and company address text",
      count: 0,
      positionClass: matchedPoint.positionClass
    };
    current.count += 1;
    clusters.set(matchedPoint.id, current);
  }

  return [...clusters.values()].sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
}

function buildProcurementGraph(graph: RelationshipGraph | null): RelationshipGraph {
  if (!graph) return { nodes: [], edges: [] };
  const allowedTypes = new Set(["company", "tender", "award", "buyer", "document", "evidence", "web_evidence"]);
  const nodes = graph.nodes.filter((node) => allowedTypes.has(node.type)).slice(0, 50);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)).slice(0, 50);
  return { nodes, edges };
}

function WorkspaceResults({ data, steps }: { data: InvestigationData; steps: InvestigationStep[] }) {
  const awards = useMemo(() => data.tenderDetails.flatMap((tender) => tender.awards.map((award) => ({ ...award, tender }))), [data.tenderDetails]);
  const procurementEvidence = useMemo(() => procurementEvidenceRows(data.webPages), [data.webPages]);
  const buyers = useMemo(() => buyerRows(data.tenders, procurementEvidence), [data.tenders, procurementEvidence]);
  const relatedCompanies = useMemo(() => {
    const companies = new Map<string, { id: string; name: string; registration_number: string | null; awards: number }>();
    for (const award of awards) {
      const current = companies.get(award.company.id);
      companies.set(award.company.id, {
        id: award.company.id,
        name: award.company.name,
        registration_number: award.company.registration_number,
        awards: (current?.awards ?? 0) + 1
      });
    }
    for (const company of data.companies) {
      const current = companies.get(company.id);
      companies.set(company.id, {
        id: company.id,
        name: company.name,
        registration_number: company.registration_number,
        awards: current?.awards ?? 0
      });
    }
    return [...companies.values()].sort((a, b) => b.awards - a.awards);
  }, [awards, data.companies]);
  const sources = useMemo(() => sourceRows(data.webResults, data.webPages, steps), [data.webResults, data.webPages, steps]);
  const categories = useMemo(() => countValues(procurementEvidence.map((item) => item.procurement_sector ?? item.tender_category)), [procurementEvidence]);
  const countries = useMemo(() => countValues(procurementEvidence.map((item) => item.country)), [procurementEvidence]);
  const companyProfiles = useMemo<CompanyProfileCard[]>(() => {
    if (data.canonicalCompanies.length > 0) {
      return data.canonicalCompanies.map((company) => ({
        id: company.id,
        name: company.canonical_name,
        registration_number: company.linked_procurement_companies[0]?.registration_number ?? null,
        href: `/companies/${company.linked_procurement_companies[0]?.id ?? company.linked_company_ids[0] ?? company.id}`,
        awards: company.linked_awards.length,
        aliases: company.aliases,
        confidence: company.confidence,
        sources: company.matched_sources.length,
        procurementRecords: company.linked_procurement_companies.length,
        webEvidence: company.linked_web_evidence.length
      }));
    }
    return relatedCompanies.slice(0, 3).map((company) => ({ ...company, href: `/companies/${company.id}` }));
  }, [data.canonicalCompanies, relatedCompanies]);
  const totalValue = sumMoney(data.tenders.map((tender) => tender.estimated_value));
  const topBuyer = buyers[0]?.name ?? "Not available";
  const timelineItems = useMemo(() => buildInvestigationTimeline(data, awards, procurementEvidence), [awards, data, procurementEvidence]);

  return (
    <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
      <aside className="space-y-5 xl:sticky xl:top-20 xl:h-[calc(100vh-6rem)] xl:overflow-y-auto">
        <SurfaceCard className="p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9AA4AF]">Current Investigation</div>
          <div className="mt-3 text-lg font-semibold leading-tight text-[#E6E8EB]">{data.scope.label}</div>
          <div className="mt-2 text-sm leading-6 text-[#9AA4AF]">Focus on the current investigation context and keep the workspace compact.</div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <StatCard label="Total Tenders" value={formatInteger(data.totalTenders)} tone="accent" />
            <StatCard label="Total Awards" value={formatInteger(awards.length)} tone="success" />
            <StatCard label="Web Evidence" value={formatInteger(data.webPages.length)} meta={`${data.duplicatesSkipped} duplicate pages skipped`} />
            <StatCard label="Procurement Value" value={totalValue === null ? "Not disclosed" : `${formatInteger(totalValue)} mixed`} tone="warning" />
          </div>
        </SurfaceCard>

        <Section eyebrow="Timeline" title="Investigation Timeline">
          <div className="space-y-3">
            {timelineItems.length === 0 ? (
              <EmptyState message="No timeline events are available for the active investigation." />
            ) : (
              timelineItems.map((item) => <TimelineStep key={`${item.label}-${item.value}`} step={item} />)
            )}
          </div>
        </Section>
      </aside>

      <div className="min-w-0 space-y-5">
        <Section eyebrow="Overview" title="Investigation Overview">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <Metric label="Scope" value={data.scope.kind === "company" ? "Company investigation" : data.scope.kind === "tender" ? "Tender investigation" : "Query investigation"} />
            <Metric label="Top buyer" value={topBuyer} />
            <Metric label="Procurement entities" value={formatInteger(procurementEvidence.length)} />
            <Metric label="Countries" value={countries.length ? countries.map((item) => `${item.name} (${item.count})`).join(", ") : "Not available"} />
          </div>
        </Section>

        <Section eyebrow="Indicators" title="Procurement Indicators">
          {data.tenders.length === 0 && procurementEvidence.length === 0 ? (
            <EmptyState title="No procurement records found" message="The existing procurement APIs and extracted web evidence returned no procurement records for this query." />
          ) : (
            <div className="grid gap-4 lg:grid-cols-3">
              <SummaryList title="Top Buyers" items={buyers.slice(0, 5).map((buyer) => `${buyer.name} (${buyer.records})`)} />
              <SummaryList title="Top Categories" items={categories.length ? categories.slice(0, 5).map((item) => `${item.name} (${item.count})`) : ["Not available"]} />
              <SummaryList title="Country Distribution" items={countries.length ? countries.slice(0, 5).map((item) => `${item.name} (${item.count})`) : ["Not available"]} />
            </div>
          )}
        </Section>

        <Section eyebrow="Evidence" title="Evidence">
          <SearchableProcurementEvidenceTable evidence={procurementEvidence} pages={data.webPages} />
        </Section>

        <Section eyebrow="Graph" title="Relationship Graph">
          {data.graph && data.graph.nodes.length > 0 ? (
            <div className="overflow-hidden rounded-[4px] border border-[#2A3441]">
              <RelationshipGraphExplorer graph={data.graph} />
            </div>
          ) : (
            <EmptyState message="Graph data is unavailable from the existing graph API." />
          )}
        </Section>

        <Section eyebrow="Tables" title="Investigation Tables">
          <div className="space-y-5">
            <SearchableTenderTable tenders={data.tenders} />
            <SearchableAwardTable awards={awards} />
            <SearchableBuyersTable buyers={buyers} />
            <SearchableWebTable pages={data.webPages} />
          </div>
        </Section>
      </div>

      <aside className="space-y-5 xl:sticky xl:top-20 xl:h-[calc(100vh-6rem)] xl:overflow-y-auto">
        <Section eyebrow="Company" title="Canonical Company">
          {companyProfiles.length === 0 ? (
            <EmptyState title="No company profile data found" message="No matching company profile is available from the existing company APIs." />
          ) : (
            <div className="space-y-3">
              {companyProfiles.map((company) => (
                <Link className="block rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3 hover:border-[#C58B2A]" href={company.href} key={company.id}>
                  <div className="text-sm font-semibold leading-snug text-[#E6E8EB]">{company.name}</div>
                  <div className="mt-1 break-words text-xs text-[#9AA4AF]">{company.registration_number ?? "No identifier"} / {company.awards} awards</div>
                  {company.aliases ? (
                    <div className="mt-2 text-xs leading-5 text-[#9AA4AF]">
                      {formatPercent(company.confidence)} confidence / {company.sources ?? 0} linked sources / {company.procurementRecords ?? 0} procurement records / {company.webEvidence ?? 0} web evidence
                      <div className="mt-1 line-clamp-2 break-words">Aliases: {company.aliases.join(", ") || "None"}</div>
                    </div>
                  ) : null}
                </Link>
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Network" title="Related Companies">
          {relatedCompanies.length === 0 ? (
            <EmptyState message="No related companies were returned by tender award details." />
          ) : (
            <div className="grid gap-3">
              {relatedCompanies.slice(0, 6).map((company) => (
                <Link className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4 transition hover:border-[#C58B2A]" href={`/companies/${company.id}`} key={company.id}>
                  <div className="text-sm font-semibold leading-snug text-[#E6E8EB]">{company.name}</div>
                  <div className="mt-1 break-words text-xs text-[#9AA4AF]">{company.registration_number ?? "No identifier"}</div>
                </Link>
              ))}
            </div>
          )}
        </Section>

        <Section eyebrow="Sources" title="Source Explorer">
          {sources.length === 0 ? (
            <EmptyState message="No public web sources were discovered for this query." />
          ) : (
            <div className="grid gap-3">
              {sources.map((source) => (
                <SourceCard key={source.domain} source={source} />
              ))}
            </div>
          )}
        </Section>
      </aside>
    </div>
  );
}

function SearchableTenderTable({ tenders }: { tenders: TenderSummary[] }) {
  const [filter, setFilter] = useState("");
  const items = filterItems(tenders, filter, (tender) => `${tender.title} ${tender.reference_number} ${tender.procuring_entity ?? ""}`);
  const columns: Column<TenderSummary>[] = [
    { key: "title", header: "Tender", render: (tender) => <RecordTitle title={tender.title} meta={tender.reference_number} /> },
    { key: "buyer", header: "Buyer", render: (tender) => <span>{tender.procuring_entity ?? "Unknown"}</span> },
    { key: "value", header: "Value", align: "right", render: (tender) => <span>{formatMoney(tender.estimated_value, tender.currency)} {tender.currency}</span> },
    { key: "published", header: "Published", render: (tender) => <span>{formatDate(tender.published_date)}</span> }
  ];
  return <WorkspaceTable title="Tender History" icon={<FileText className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No tenders match this investigation." />} getHref={(tender) => `/tenders/${tender.id}`} items={items} /></WorkspaceTable>;
}

function SearchableAwardTable({ awards }: { awards: Array<TenderDetail["awards"][number] & { tender: TenderDetail }> }) {
  const [filter, setFilter] = useState("");
  const items = filterItems(awards, filter, (award) => `${award.company.name} ${award.tender.title} ${award.currency}`);
  const columns: Column<(typeof awards)[number]>[] = [
    { key: "company", header: "Company", render: (award) => <RecordTitle title={award.company.name} meta={award.company.registration_number ?? "No identifier"} /> },
    { key: "tender", header: "Tender", render: (award) => <span>{award.tender.title}</span> },
    { key: "amount", header: "Award Value", align: "right", render: (award) => <span>{formatMoney(award.award_value, award.currency)} {award.currency}</span> },
    { key: "date", header: "Award Date", render: (award) => <span>{formatDate(award.award_date)}</span> }
  ];
  return <WorkspaceTable title="Award History" icon={<Award className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No award history is available from tender details." />} items={items} /></WorkspaceTable>;
}

function SearchableProcurementEvidenceTable({ evidence, pages }: { evidence: ProcurementEvidence[]; pages: StoredWebPage[] }) {
  const [filter, setFilter] = useState("");
  const pageByEvidenceId = new Map(pages.map((page) => [page.procurement_evidence?.id, page]));
  const items = filterItems(evidence, filter, (item) => `${item.company_name ?? ""} ${item.government_buyer ?? ""} ${item.tender_title ?? ""} ${item.contract_title ?? ""} ${item.country ?? ""}`);
  const columns: Column<ProcurementEvidence>[] = [
    { key: "company", header: "Company", render: (item) => <RecordTitle title={item.company_name ?? item.normalized_company_name ?? "Unknown company"} meta={item.organization ?? "Extracted from web evidence"} /> },
    { key: "buyer", header: "Government Buyer", render: (item) => <span>{item.government_buyer ?? "Not available"}</span> },
    { key: "procurement", header: "Procurement", render: (item) => <RecordTitle title={item.tender_title ?? item.contract_title ?? "Untitled procurement evidence"} meta={item.tender_number ?? item.contract_number ?? item.procurement_sector ?? "No reference number"} /> },
    { key: "value", header: "Value", align: "right", render: (item) => <span>{item.contract_value ? formatMoney(item.contract_value, item.currency ?? "") : "Not disclosed"} {item.currency ?? ""}</span> },
    { key: "source", header: "Source", render: (item) => {
      const page = pageByEvidenceId.get(item.id);
      return page ? <a className="break-all text-[#F3D59A] hover:underline" href={page.url} rel="noreferrer" target="_blank">{page.source}</a> : <span>Stored evidence</span>;
    } }
  ];
  return <WorkspaceTable title="Procurement Evidence" icon={<Shield className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No procurement facts were extracted from web evidence." />} items={items} /></WorkspaceTable>;
}

function CanonicalCompanyTable({ companies }: { companies: CanonicalCompany[] }) {
  const [filter, setFilter] = useState("");
  const items = filterItems(companies, filter, (company) => `${company.canonical_name} ${company.aliases.join(" ")}`);
  const columns: Column<CanonicalCompany>[] = [
    { key: "name", header: "Canonical Name", render: (company) => <RecordTitle title={company.canonical_name} meta={`${company.linked_procurement_companies.length} procurement records`} /> },
    { key: "aliases", header: "Aliases", render: (company) => <span>{company.aliases.join(", ") || "None"}</span> },
    { key: "confidence", header: "Confidence", align: "right", render: (company) => <span>{formatPercent(company.confidence)}</span> },
    { key: "sources", header: "Linked Sources", render: (company) => <span>{company.matched_sources.length} sources / {company.linked_web_evidence.length} web evidence</span> }
  ];
  return <WorkspaceTable title="Canonical Entities" icon={<Users className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No canonical entity links were returned for this investigation." />} items={items} /></WorkspaceTable>;
}

function SearchableBuyersTable({ buyers }: { buyers: Array<{ id: string; name: string; records: number }> }) {
  const [filter, setFilter] = useState("");
  const items = filterItems(buyers, filter, (buyer) => buyer.name);
  const columns: Column<(typeof buyers)[number]>[] = [
    { key: "buyer", header: "Government Buyer", render: (buyer) => <span className="font-semibold">{buyer.name}</span> },
    { key: "records", header: "Records", align: "right", render: (buyer) => <span>{buyer.records}</span> },
    { key: "documents", header: "Documents", render: () => <span>Not available</span> }
  ];
  return <WorkspaceTable title="Government Buyers" icon={<Landmark className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No government buyers were returned by procurement records." />} items={items} /></WorkspaceTable>;
}

function BidHistoryTable() {
  const [filter, setFilter] = useState("");
  return (
    <WorkspaceTable title="Bid History" icon={<Table2 className="h-4 w-4" />} filter={filter} onFilter={setFilter}>
      <EmptyState
        title="No bid history available"
        message="The existing backend APIs do not expose bid-level records for this investigation."
      />
    </WorkspaceTable>
  );
}

function SearchableWebTable({ pages }: { pages: StoredWebPage[] }) {
  const [filter, setFilter] = useState("");
  const items = filterItems(pages, filter, (page) => `${page.title ?? ""} ${page.source} ${page.url}`);
  const columns: Column<StoredWebPage>[] = [
    { key: "source", header: "Source", render: (page) => <RecordTitle title={page.title ?? page.source} meta={page.source} /> },
    { key: "url", header: "URL", render: (page) => <a className="break-all text-[#F3D59A] hover:underline" href={page.url} rel="noreferrer" target="_blank">{page.url}</a> },
    { key: "retrieved", header: "Retrieved", render: (page) => <span>{formatDate(page.retrieved_at)}</span> },
    { key: "entities", header: "Entities", align: "right", render: (page) => <span>{page.extraction.organization_names.length}</span> }
  ];
  return <WorkspaceTable title="Web Evidence" icon={<Globe2 className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No web evidence pages were stored for this query." />} items={items} /></WorkspaceTable>;
}

function WorkspaceTable({ children, filter, icon, onFilter, title }: { children: ReactNode; filter: string; icon: ReactNode; onFilter: (value: string) => void; title: string }) {
  return (
    <Section
      eyebrow="Table"
      title={title}
      action={
        <label className="relative">
          <span className="sr-only">Search {title}</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9AA4AF]" />
          <input className="h-9 w-44 rounded-[4px] border border-[#2A3441] bg-[#0B0F14] pl-8 pr-3 text-xs text-[#E6E8EB] placeholder:text-[#6f7a86] sm:w-56" onChange={(event) => onFilter(event.target.value)} placeholder="Search table" value={filter} />
        </label>
      }
    >
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">
        {icon}
        <span className="truncate">{title}</span>
      </div>
      {children}
    </Section>
  );
}

function InvestigationConsole({ activeQuery, running, steps }: { activeQuery: string; running: boolean; steps: InvestigationStep[] }) {
  return (
    <SurfaceCard className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9AA4AF]">Live Console</div>
          <div className="mt-1 text-sm font-semibold text-[#E6E8EB]">{activeQuery || "Awaiting search"}</div>
        </div>
        {running ? <Loader2 className="h-4 w-4 animate-spin text-[#C58B2A]" /> : <Activity className="h-4 w-4 text-[#667A52]" />}
      </div>
      <div className="mt-4 space-y-2">
        {steps.map((step) => (
          <motion.div animate={{ opacity: 1, x: 0 }} className="grid grid-cols-[22px_1fr_auto] gap-3 border border-[#2A3441] bg-[#0B0F14] p-2.5" initial={{ opacity: 0, x: -8 }} key={step.name}>
            <StepIcon status={step.status} />
            <div>
              <div className="text-sm font-semibold text-[#E6E8EB]">{step.name}</div>
              <div className="mt-1 text-xs text-[#9AA4AF]">{step.detail ?? (step.status === "pending" ? "Pending" : "Running")}</div>
            </div>
            <div className="text-right text-xs tabular-nums text-[#9AA4AF]">
              <div>{step.durationMs !== undefined ? `${step.durationMs} ms` : "--"}</div>
              <div>{step.recordsFound !== undefined ? `${step.recordsFound} records` : ""}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </SurfaceCard>
  );
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "complete") return <span className="mt-0.5 flex h-5 w-5 items-center justify-center border border-[#667A52] text-[#8DA175]"><Check className="h-3.5 w-3.5" /></span>;
  if (status === "running") return <span className="mt-0.5 flex h-5 w-5 items-center justify-center border border-[#C58B2A] text-[#F3D59A]"><Loader2 className="h-3.5 w-3.5 animate-spin" /></span>;
  if (status === "error") return <span className="mt-0.5 h-5 w-5 border border-[#8F3A3A] bg-[#2A1414]" />;
  return <span className="mt-0.5 h-5 w-5 border border-[#2A3441] bg-[#121821]" />;
}

function TimelineStep({ step }: { step: TimelineItem }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
      <div className="flex items-start gap-2 text-sm font-semibold text-[#E6E8EB]"><Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-[#C58B2A]" aria-hidden="true" /><span className="min-w-0 break-words leading-5">{step.label}</span></div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[#9AA4AF]">
        <span>Value</span><span className="break-words text-right">{step.value}</span>
        <span className="col-span-2 break-words leading-5">{step.detail ?? "Not available"}</span>
      </div>
    </div>
  );
}

function SourceCard({ source }: { source: { domain: string; name: string; records: number; documents: number; lastUpdate: string; executionTime: string } }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
      <div className="flex items-start gap-3">
        <img alt="" className="mt-0.5 h-6 w-6 rounded-[3px] bg-[#0B0F14]" src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(source.domain)}&sz=64`} />
        <div className="min-w-0 flex-1">
          <div className="line-clamp-2 text-sm font-semibold leading-5 text-[#E6E8EB]">{source.name}</div>
          <div className="mt-1 break-all text-xs text-[#9AA4AF]">{source.domain}</div>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <SourceFact label="Records" value={String(source.records)} />
        <SourceFact label="Documents" value={String(source.documents)} />
        <SourceFact label="Last update" value={source.lastUpdate} />
        <SourceFact label="Execution" value={source.executionTime} />
      </div>
    </div>
  );
}

function SourceFact({ label, value }: { label: string; value: string }) {
  return <div><div className="text-[#9AA4AF]">{label}</div><div className="mt-1 break-words font-semibold leading-5 tabular-nums text-[#E6E8EB]">{value}</div></div>;
}

function SummaryList({ items, title }: { items: string[]; title: string }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">{title}</div>
      <div className="mt-3 space-y-2">
        {items.map((item) => <div className="break-words text-sm leading-6 text-[#E6E8EB]" key={item}>{item}</div>)}
      </div>
    </div>
  );
}

function RecordTitle({ meta, title }: { meta: string; title: string }) {
  return <div className="min-w-0"><div className="line-clamp-2 break-words font-semibold leading-5 text-[#E6E8EB]">{title}</div><div className="mt-1 break-words text-xs leading-5 text-[#9AA4AF]">{meta}</div></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0 rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3"><div className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{label}</div><div className="mt-2 break-words text-sm font-semibold leading-5 text-[#E6E8EB]">{value}</div></div>;
}

function StartState() {
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      {["Procurement records", "Public web evidence", "Relationship graph"].map((label) => (
        <SurfaceCard className="p-5" key={label}>
          <Database className="h-5 w-5 text-[#C58B2A]" />
          <div className="mt-4 text-sm font-semibold text-[#E6E8EB]">{label}</div>
          <div className="mt-2 text-sm text-[#9AA4AF]">Search to begin collecting live evidence from existing APIs.</div>
        </SurfaceCard>
      ))}
    </div>
  );
}

function LoadingWorkspace() {
  return (
    <AnimatePresence>
      <motion.div animate={{ opacity: 1 }} className="grid gap-5 lg:grid-cols-4" initial={{ opacity: 0 }}>
        <SkeletonBlock className="h-28 rounded-[6px]" />
        <SkeletonBlock className="h-28 rounded-[6px]" />
        <SkeletonBlock className="h-28 rounded-[6px]" />
        <SkeletonBlock className="h-28 rounded-[6px]" />
      </motion.div>
    </AnimatePresence>
  );
}

function createSteps(): InvestigationStep[] {
  return stepNames.map((name) => ({ name, status: "pending" }));
}

function buyerRows(tenders: TenderSummary[], evidence: ProcurementEvidence[] = []) {
  const buyers = new Map<string, { id: string; name: string; records: number }>();
  for (const tender of tenders) {
    const name = tender.procuring_entity ?? "Unknown";
    const id = name.toLowerCase();
    buyers.set(id, { id, name, records: (buyers.get(id)?.records ?? 0) + 1 });
  }
  for (const item of evidence) {
    if (!item.government_buyer) continue;
    const id = item.government_buyer.toLowerCase();
    buyers.set(id, { id, name: item.government_buyer, records: (buyers.get(id)?.records ?? 0) + 1 });
  }
  return [...buyers.values()].sort((a, b) => b.records - a.records);
}

function sourceRows(results: WebSearchResult[], pages: StoredWebPage[], steps: InvestigationStep[]) {
  const webStep = steps.find((step) => step.name === "Searching Web");
  const sources = new Map<string, { domain: string; name: string; records: number; documents: number; lastUpdate: string; executionTime: string }>();
  for (const result of results) {
    sources.set(result.domain, {
      domain: result.domain,
      name: result.source || result.domain,
      records: 0,
      documents: 0,
      lastUpdate: result.published_date ? formatDate(result.published_date) : "Not available",
      executionTime: webStep?.durationMs !== undefined ? `${webStep.durationMs} ms` : "Not available"
    });
  }
  for (const page of pages) {
    const current = sources.get(page.source) ?? {
      domain: page.source,
      name: page.source,
      records: 0,
      documents: 0,
      lastUpdate: "Not available",
      executionTime: webStep?.durationMs !== undefined ? `${webStep.durationMs} ms` : "Not available"
    };
    sources.set(page.source, {
      ...current,
      records: current.records + 1,
      documents: current.documents + 1,
      lastUpdate: formatDate(page.retrieved_at)
    });
  }
  return [...sources.values()];
}

function filterItems<T>(items: T[], filter: string, text: (item: T) => string): T[] {
  const normalized = filter.trim().toLowerCase();
  if (!normalized) return items;
  return items.filter((item) => text(item).toLowerCase().includes(normalized));
}

function mergeWebPages(primary: StoredWebPage[], secondary: StoredWebPage[]): StoredWebPage[] {
  const pages = new Map<string, StoredWebPage>();
  for (const page of [...primary, ...secondary]) {
    pages.set(page.id, page);
  }
  return [...pages.values()];
}

function procurementEvidenceRows(pages: StoredWebPage[]): ProcurementEvidence[] {
  const evidence = new Map<string, ProcurementEvidence>();
  for (const page of pages) {
    if (page.procurement_evidence) {
      evidence.set(page.procurement_evidence.id, page.procurement_evidence);
    }
  }
  return [...evidence.values()];
}

function uniqueStrings(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => Boolean(value)))];
}

function uniqueCanonicalCompanies(values: CanonicalCompany[]): CanonicalCompany[] {
  const companies = new Map<string, CanonicalCompany>();
  for (const company of values) {
    companies.set(company.id, company);
  }
  return [...companies.values()];
}

function toTenderSummary(tender: TenderDetail): TenderSummary {
  const { awards: _awards, buyer: _buyer, description: _description, participating_companies: _participatingCompanies, ...summary } = tender;
  return summary;
}

function countValues(values: Array<string | null | undefined>): Array<{ name: string; count: number }> {
  const counts = new Map<string, number>();
  for (const value of values) {
    if (!value) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

function sumMoney(values: Array<string | null>): number | null {
  const numbers = values.map((value) => Number(value)).filter(Number.isFinite);
  if (numbers.length === 0) return null;
  return Math.round(numbers.reduce((total, value) => total + value, 0));
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("en").format(value);
}

function formatPercent(value: string | undefined): string {
  if (!value) return "Not available";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "Not available";
  return `${Math.round(numeric * 100)}%`;
}

type TimelineItem = {
  label: string;
  value: string;
  detail?: string;
};

function buildInvestigationTimeline(data: InvestigationData, awards: Array<TenderDetail["awards"][number] & { tender: TenderDetail }>, evidence: ProcurementEvidence[]): TimelineItem[] {
  const items: TimelineItem[] = [];

  if (data.scope.kind === "company") {
    const overview = data.companyOverviews[0];
    if (overview) {
      items.push(
        { label: "First procurement", value: formatDate(overview.first_procurement_date ?? null), detail: `${overview.total_tenders} tenders in scope` },
        { label: "Latest procurement", value: formatDate(overview.latest_procurement_date ?? null), detail: `${overview.total_awards_won} awards in scope` },
        { label: "Company added", value: formatDate(overview.company.created_at), detail: overview.company.name },
        { label: "Record updated", value: formatDate(overview.company.updated_at), detail: overview.registration_identifier ?? "No registration identifier" }
      );
    }
  }

  for (const tender of data.tenderDetails.slice(0, 5)) {
    items.push(
      { label: `Tender published`, value: formatDate(tender.published_date ?? null), detail: tender.reference_number },
      { label: `Tender closing`, value: formatDate(tender.closing_date ?? null), detail: tender.title }
    );
  }

  for (const award of awards.slice(0, 5)) {
    items.push({ label: "Award", value: formatDate(award.award_date ?? null), detail: `${award.company.name} / ${formatMoney(award.award_value, award.currency)} ${award.currency}` });
  }

  for (const page of data.webPages.slice(0, 5)) {
    items.push({ label: "Evidence retrieved", value: formatDate(page.retrieved_at), detail: page.title ?? page.source });
  }

  for (const item of evidence.slice(0, 5)) {
    if (item.publication_date) {
      items.push({ label: "Public record", value: formatDate(item.publication_date), detail: item.tender_title ?? item.contract_title ?? item.company_name ?? "Evidence" });
    }
  }

  return items.slice(0, 12);
}

function selectPrimaryCompany(companies: CompanySearchSummary[], query: string): CompanySearchSummary | null {
  if (companies.length === 0) return null;
  const normalized = query.trim().toLowerCase();
  return [...companies]
    .map((company) => ({ company, score: scoreText(company.name, normalized, company.registration_number ?? "") }))
    .sort((left, right) => right.score - left.score || left.company.name.localeCompare(right.company.name))[0]
    ?.company ?? companies[0] ?? null;
}

function selectPrimaryTender(tenders: TenderSummary[], query: string): TenderSummary | null {
  if (tenders.length === 0) return null;
  const normalized = query.trim().toLowerCase();
  return [...tenders]
    .map((tender) => ({ tender, score: scoreText(tender.title, normalized, tender.reference_number, tender.procuring_entity ?? "") }))
    .sort((left, right) => right.score - left.score || left.tender.title.localeCompare(right.tender.title))[0]
    ?.tender ?? tenders[0] ?? null;
}

function scoreText(primary: string, query: string, ...extra: string[]): number {
  const haystack = [primary, ...extra].join(" ").toLowerCase();
  if (!query) return 0;
  if (haystack === query) return 100;
  if (haystack.includes(query)) return 50;
  return query.split(/\s+/).filter(Boolean).reduce((score, token) => score + (haystack.includes(token) ? 10 : 0), 0);
}

function matchesQuery(values: Array<string | null | undefined>, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return false;
  return values.some((value) => (value ?? "").toLowerCase().includes(normalized));
}

function filterWebPages(pages: StoredWebPage[], scope: InvestigationScope, query: string): StoredWebPage[] {
  if (scope.kind === "company") {
    return pages.filter((page) => {
      const evidence = page.procurement_evidence;
      return Boolean(
        evidence &&
        (evidence.company_id === scope.id ||
          matchesQuery([evidence.company_name, evidence.normalized_company_name, page.title, page.source, page.url], scope.label) ||
          matchesQuery(page.extraction.company_mentions, scope.label) ||
          matchesQuery(page.extraction.organization_names, scope.label))
      );
    });
  }

  if (scope.kind === "tender") {
    return pages.filter((page) => {
      const evidence = page.procurement_evidence;
      return Boolean(
        evidence &&
        (evidence.tender_id === scope.id ||
          matchesQuery([evidence.tender_title, evidence.contract_title, page.title, page.source, page.url], scope.label))
      );
    });
  }

  return pages.filter((page) => matchesQuery([page.title, page.source, page.url, page.query], query));
}
