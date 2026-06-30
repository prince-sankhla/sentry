"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Award,
  Check,
  Database,
  FileText,
  Globe2,
  Landmark,
  Loader2,
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

export function InvestigationWorkspace({ initialQuery }: { initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [steps, setSteps] = useState<InvestigationStep[]>(() => createSteps());
  const [data, setData] = useState<InvestigationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (initialQuery) {
      runInvestigation(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        investigation.tenders = tenders.items;
        investigation.companies = companies.items;
        investigation.dashboardSummary = dashboardSummary;
        investigation.dashboardRecent = dashboardRecent;
        investigation.totalTenders = tenders.pagination.total;
        const detailCandidates = tenders.items.slice(0, 8);
        investigation.tenderDetails = await Promise.all(
          detailCandidates.map((tender) => getTender(tender.id).catch(() => null))
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
        investigation.webPages = mergeWebPages(web.stored_pages, storedProcurement.items);
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
        const primaryCompanyId = investigation.companies[0]?.id ?? evidence.find((item) => item.company_id)?.company_id ?? undefined;
        const primaryTenderId = investigation.tenders[0]?.id ?? evidence.find((item) => item.tender_id)?.tender_id ?? undefined;
        const companyIds = uniqueStrings([
          ...investigation.companies.slice(0, 3).map((company) => company.id),
          ...evidence.map((item) => item.company_id).filter((value): value is string => Boolean(value))
        ]).slice(0, 3);

        const companyPayloads = await Promise.all(
          companyIds.map(async (companyId) => {
            const [overview, tenders, awards, canonical] = await Promise.all([
              getCompanyOverview(companyId).catch(() => null),
              getCompanyTenders(companyId, { limit: 25 }).catch(() => null),
              getCompanyAwards(companyId, 25).catch(() => null),
              getCanonicalCompany(companyId).catch(() => null)
            ]);
            return { overview, tenders, awards, canonical };
          })
        );
        investigation.companyOverviews = companyPayloads.map((item) => item.overview).filter((item): item is CompanyOverview => item !== null);
        investigation.companyTenderHistory = companyPayloads.flatMap((item) => item.tenders?.items ?? []);
        investigation.companyAwardHistory = companyPayloads.flatMap((item) => item.awards?.items ?? []);
        investigation.canonicalCompanies = uniqueCanonicalCompanies(
          companyPayloads.map((item) => item.canonical).filter((item): item is CanonicalCompany => item !== null)
        );
        investigation.graph = await getRelationshipGraph({
          companyId: primaryCompanyId,
          tenderId: primaryCompanyId ? undefined : primaryTenderId,
          depth: 2
        }).catch(() => getRelationshipGraph({ depth: 2 }).catch(() => null));
        return {
          recordsFound: (investigation.graph?.nodes.length ?? 0) + (investigation.graph?.edges.length ?? 0),
          detail: investigation.graph ? "Company, history, and graph APIs loaded" : "Company history loaded; graph unavailable"
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
    <main className="min-h-screen bg-[#0B0F14]">
      <section className="border-b border-[#2A3441] bg-[#10151D]">
        <div className="mx-auto grid w-full max-w-7xl gap-5 px-5 py-7 sm:px-8 xl:grid-cols-[1fr_420px]">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#C58B2A]">
              <Shield className="h-4 w-4" aria-hidden="true" />
              Investigation Workspace
            </div>
            <h1 className="mt-3 max-w-4xl text-3xl font-semibold text-[#E6E8EB] sm:text-5xl">
              Search a company. Watch the investigation unfold.
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-[#9AA4AF]">
              SENTRY searches procurement records, public web evidence, and investigation graphs using the existing backend APIs.
            </p>
            <form className="mt-6 flex flex-col gap-3 sm:flex-row" onSubmit={onSubmit}>
              <label className="relative flex-1">
                <span className="sr-only">Investigation search query</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA4AF]" />
                <input
                  className="h-12 w-full rounded-[4px] border border-[#2A3441] bg-[#0B0F14] pl-10 pr-3 text-sm text-[#E6E8EB] outline-none placeholder:text-[#6f7a86] focus:border-[#C58B2A]"
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Reliance Jio, TCS, Infosys, Adani"
                  type="search"
                  value={query}
                />
              </label>
              <button
                className="inline-flex h-12 items-center justify-center gap-2 rounded-[4px] border border-[#C58B2A] bg-[#1F1A12] px-5 text-sm font-semibold text-[#F3D59A] transition hover:bg-[#2A2115] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={running}
                type="submit"
              >
                {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Start Investigation
              </button>
            </form>
          </div>
          <InvestigationConsole activeQuery={activeQuery} running={running} steps={steps} />
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl space-y-5 px-5 py-6 sm:px-8">
        {error ? <ErrorState title="Investigation failed" message={error} /> : null}
        {!activeQuery && !data && !running ? <StartState /> : null}
        {running && !data ? <LoadingWorkspace /> : null}
        {data ? <WorkspaceResults data={data} steps={steps} /> : null}
      </section>
    </main>
  );
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

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Tenders" value={formatInteger(data.totalTenders)} tone="accent" />
        <StatCard label="Total Awards" value={formatInteger(awards.length)} tone="success" />
        <StatCard label="Procurement Value" value={totalValue === null ? "Not disclosed" : `${formatInteger(totalValue)} mixed`} tone="warning" />
        <StatCard label="Web Evidence" value={formatInteger(data.webPages.length)} meta={`${data.duplicatesSkipped} duplicate pages skipped`} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <Section eyebrow="Overview" title="Investigation Overview">
          <div className="grid gap-3 sm:grid-cols-2">
            <Metric label="Query" value={data.query} />
            <Metric label="Top buyer" value={topBuyer} />
            <Metric label="Procurement entities" value={formatInteger(procurementEvidence.length)} />
            <Metric label="Backend totals" value={data.dashboardSummary ? `${formatInteger(data.dashboardSummary.total_tenders)} tenders / ${formatInteger(data.dashboardSummary.total_companies)} companies` : "Not available"} />
            <Metric label="Country distribution" value={countries.length ? countries.map((item) => `${item.name} (${item.count})`).join(", ") : "Not available"} />
          </div>
        </Section>
        <Section eyebrow="Company" title="Canonical Company">
          {companyProfiles.length === 0 ? (
            <EmptyState title="No company profile data found" message="No matching company profile is available from the existing company APIs." />
          ) : (
            <div className="space-y-3">
              {companyProfiles.map((company) => (
                <Link className="block rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3 hover:border-[#C58B2A]" href={company.href} key={company.id}>
                  <div className="text-sm font-semibold text-[#E6E8EB]">{company.name}</div>
                  <div className="mt-1 text-xs text-[#9AA4AF]">{company.registration_number ?? "No identifier"} / {company.awards} awards</div>
                  {company.aliases ? (
                    <div className="mt-2 text-xs text-[#9AA4AF]">
                      {formatPercent(company.confidence)} confidence / {company.sources ?? 0} linked sources / {company.procurementRecords ?? 0} procurement records / {company.webEvidence ?? 0} web evidence
                      <div className="mt-1 line-clamp-2">Aliases: {company.aliases.join(", ") || "None"}</div>
                    </div>
                  ) : null}
                </Link>
              ))}
            </div>
          )}
        </Section>
      </div>

      <Section eyebrow="Procurement" title="Procurement Summary">
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

      <SearchableTenderTable tenders={data.tenders} />
      <SearchableAwardTable awards={awards} />
      <SearchableProcurementEvidenceTable evidence={procurementEvidence} pages={data.webPages} />
      <CanonicalCompanyTable companies={data.canonicalCompanies} />
      <BidHistoryTable />
      <SearchableBuyersTable buyers={buyers} />
      <SearchableWebTable pages={data.webPages} />

      <Section eyebrow="Network" title="Related Companies">
        {relatedCompanies.length === 0 ? (
          <EmptyState message="No related companies were returned by tender award details." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {relatedCompanies.map((company) => (
              <Link className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4 transition hover:border-[#C58B2A]" href={`/companies/${company.id}`} key={company.id}>
                <Users className="h-4 w-4 text-[#667A52]" aria-hidden="true" />
                <div className="mt-2 text-sm font-semibold text-[#E6E8EB]">{company.name}</div>
                <div className="mt-1 text-xs text-[#9AA4AF]">{company.registration_number ?? "No identifier"}</div>
              </Link>
            ))}
          </div>
        )}
      </Section>

      <Section eyebrow="Sources" title="Source Explorer">
        {sources.length === 0 ? (
          <EmptyState message="No public web sources were discovered for this query." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {sources.map((source) => (
              <SourceCard key={source.domain} source={source} />
            ))}
          </div>
        )}
      </Section>

      <Section eyebrow="Timeline" title="Investigation Timeline">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {steps.map((step) => <TimelineStep key={step.name} step={step} />)}
        </div>
      </Section>

      <Section eyebrow="Graph" title="Investigation Graph">
        {data.graph && data.graph.nodes.length > 0 ? (
          <div className="h-[760px] overflow-hidden rounded-[4px] border border-[#2A3441]">
            <RelationshipGraphExplorer graph={data.graph} />
          </div>
        ) : (
          <EmptyState message="Graph data is unavailable from the existing graph API." />
        )}
      </Section>
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
          <input className="h-9 w-56 rounded-[4px] border border-[#2A3441] bg-[#0B0F14] pl-8 pr-3 text-xs text-[#E6E8EB]" onChange={(event) => onFilter(event.target.value)} placeholder="Search table" value={filter} />
        </label>
      }
    >
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">{icon}{title}</div>
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

function TimelineStep({ step }: { step: InvestigationStep }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB]"><StepIcon status={step.status} />{step.name}</div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[#9AA4AF]">
        <span>Duration</span><span className="text-right tabular-nums">{step.durationMs !== undefined ? `${step.durationMs} ms` : "Not available"}</span>
        <span>Records</span><span className="text-right tabular-nums">{step.recordsFound ?? "Not available"}</span>
      </div>
    </div>
  );
}

function SourceCard({ source }: { source: { domain: string; name: string; records: number; documents: number; lastUpdate: string; executionTime: string } }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
      <div className="flex items-start gap-3">
        <img alt="" className="mt-0.5 h-6 w-6 rounded-[3px] bg-[#0B0F14]" src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(source.domain)}&sz=64`} />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-[#E6E8EB]">{source.name}</div>
          <div className="mt-1 truncate text-xs text-[#9AA4AF]">{source.domain}</div>
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
  return <div><div className="text-[#9AA4AF]">{label}</div><div className="mt-1 font-semibold tabular-nums text-[#E6E8EB]">{value}</div></div>;
}

function SummaryList({ items, title }: { items: string[]; title: string }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">{title}</div>
      <div className="mt-3 space-y-2">
        {items.map((item) => <div className="text-sm text-[#E6E8EB]" key={item}>{item}</div>)}
      </div>
    </div>
  );
}

function RecordTitle({ meta, title }: { meta: string; title: string }) {
  return <div><div className="font-semibold text-[#E6E8EB]">{title}</div><div className="mt-1 text-xs text-[#9AA4AF]">{meta}</div></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3"><div className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{label}</div><div className="mt-2 text-sm font-semibold text-[#E6E8EB]">{value}</div></div>;
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
