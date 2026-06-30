"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Award,
  Check,
  Clock3,
  Database,
  FileText,
  Globe2,
  Landmark,
  Loader2,
  Pin,
  Search,
  PanelRight,
  Shield,
  Table2,
  Users
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from "react";

import { RelationshipGraphExplorer } from "@/app/graph/relationship-graph";
import { Section, StatCard, SurfaceCard } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState, ErrorState, SkeletonBlock } from "@/components/ui/states";
import { Timeline } from "@/components/ui/timeline";
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
import type { RelationshipGraphSelection } from "@/app/graph/relationship-graph";

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

type WorkspaceSelectionKind =
  | "overview"
  | "company"
  | "tender"
  | "award"
  | "buyer"
  | "evidence"
  | "document"
  | "source"
  | "timeline"
  | "indicator"
  | "graph-node"
  | "graph-edge";

type WorkspaceSelection = {
  kind: WorkspaceSelectionKind;
  id: string;
  label: string;
  meta?: string;
};

type InvestigationHistoryEntry = {
  query: string;
  label: string;
  updatedAt: string;
};

type SelectionTarget = {
  label: string;
  selection: WorkspaceSelection;
};

type DetailItem = {
  label: string;
  value: string;
  target?: SelectionTarget;
};

type SelectionDetail = {
  badge: string;
  title: string;
  summary: string;
  properties: DetailItem[];
  relationships: DetailItem[];
  evidence: DetailItem[];
  documents: DetailItem[];
  timeline: DetailItem[];
  relatedRecords: DetailItem[];
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
  const [selectedSelection, setSelectedSelection] = useState<WorkspaceSelection>({ kind: "overview", id: "overview", label: "Investigation overview" });
  const [recentInvestigations, setRecentInvestigations] = useState<InvestigationHistoryEntry[]>([]);
  const [pinnedInvestigations, setPinnedInvestigations] = useState<InvestigationHistoryEntry[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setRecentInvestigations(readInvestigationHistory(window.localStorage.getItem(RECENT_STORAGE_KEY)));
    setPinnedInvestigations(readInvestigationHistory(window.localStorage.getItem(PINNED_STORAGE_KEY)));
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(recentInvestigations));
  }, [recentInvestigations]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(pinnedInvestigations));
  }, [pinnedInvestigations]);

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
      setSelectedSelection({ kind: "overview", id: "overview", label: normalized, meta: "Current investigation overview" });
      setRecentInvestigations((current) => upsertInvestigationHistory(current, { query: normalized, label: normalized, updatedAt: new Date().toISOString() }));
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

  function pinCurrentInvestigation() {
    const normalized = activeQuery.trim();
    if (!normalized) return;

    setPinnedInvestigations((current) =>
      upsertInvestigationHistory(current, {
        query: normalized,
        label: normalized,
        updatedAt: new Date().toISOString()
      })
    );
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
        {data ? (
          <WorkspaceResults
            data={data}
            onPinCurrent={pinCurrentInvestigation}
            onRunInvestigation={runInvestigation}
            onSelectSelection={setSelectedSelection}
            onSetPinnedInvestigations={setPinnedInvestigations}
            onSetRecentInvestigations={setRecentInvestigations}
            pinnedInvestigations={pinnedInvestigations}
            recentInvestigations={recentInvestigations}
            selectedSelection={selectedSelection}
            steps={steps}
          />
        ) : null}
      </section>
    </main>
  );
}

function WorkspaceResults({
  data,
  onPinCurrent,
  onRunInvestigation,
  onSelectSelection,
  onSetPinnedInvestigations,
  onSetRecentInvestigations,
  pinnedInvestigations,
  recentInvestigations,
  selectedSelection,
  steps
}: {
  data: InvestigationData;
  onPinCurrent: () => void;
  onRunInvestigation: (query: string) => void;
  onSelectSelection: (selection: WorkspaceSelection) => void;
  onSetPinnedInvestigations: Dispatch<SetStateAction<InvestigationHistoryEntry[]>>;
  onSetRecentInvestigations: Dispatch<SetStateAction<InvestigationHistoryEntry[]>>;
  pinnedInvestigations: InvestigationHistoryEntry[];
  recentInvestigations: InvestigationHistoryEntry[];
  selectedSelection: WorkspaceSelection;
  steps: InvestigationStep[];
}) {
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
  const selectionDetail = useMemo(
    () =>
      buildSelectionDetail({
        activeQuery: data.query,
        awards,
        buyers,
        categories,
        companyProfiles,
        countries,
        data,
        onSelectSelection,
        procurementEvidence,
        recentInvestigations,
        relatedCompanies,
        selectedSelection,
        sources,
        steps,
        topBuyer,
        totalValue
      }),
    [
      awards,
      buyers,
      categories,
      companyProfiles,
      countries,
      data,
      onSelectSelection,
      procurementEvidence,
      recentInvestigations,
      relatedCompanies,
      selectedSelection,
      sources,
      steps,
      topBuyer,
      totalValue
    ]
  );

  return (
    <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
      <aside className="space-y-5 xl:sticky xl:top-20 xl:h-[calc(100vh-5rem)] xl:overflow-y-auto">
        <SurfaceCard className="p-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#9AA4AF]">
            <PanelRight className="h-4 w-4 text-[#C58B2A]" />
            Workspace
          </div>
          <div className="mt-3 text-sm font-semibold text-[#E6E8EB]">{data.query || "Awaiting investigation"}</div>
          <div className="mt-1 text-xs text-[#9AA4AF]">Keep the current investigation open while moving between records.</div>
          <button className="mt-4 inline-flex h-9 items-center gap-2 rounded-[4px] border border-[#2A3441] bg-[#171F2A] px-3 text-xs font-semibold text-[#E6E8EB] transition hover:border-[#C58B2A]" onClick={onPinCurrent} type="button">
            <Pin className="h-3.5 w-3.5" />
            Pin current investigation
          </button>
        </SurfaceCard>

        <HistoryRail
          items={recentInvestigations}
          onDelete={(queryToRemove) => onSetRecentInvestigations((current) => current.filter((item) => item.query !== queryToRemove))}
          onSelect={(queryToRun) => {
            onRunInvestigation(queryToRun);
            onSelectSelection({ kind: "overview", id: "overview", label: queryToRun });
          }}
          title="Recent Investigations"
          onOpen={(queryToRun) => {
            onRunInvestigation(queryToRun);
            onSelectSelection({ kind: "overview", id: "overview", label: queryToRun });
          }}
        />

        <HistoryRail
          items={pinnedInvestigations}
          onDelete={(queryToRemove) => onSetPinnedInvestigations((current) => current.filter((item) => item.query !== queryToRemove))}
          onSelect={(queryToRun) => {
            onRunInvestigation(queryToRun);
            onSelectSelection({ kind: "overview", id: "overview", label: queryToRun });
          }}
          title="Pinned Investigations"
          onOpen={(queryToRun) => {
            onRunInvestigation(queryToRun);
            onSelectSelection({ kind: "overview", id: "overview", label: queryToRun });
          }}
        />
      </aside>

      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total Tenders" value={formatInteger(data.totalTenders)} tone="accent" />
          <StatCard label="Total Awards" value={formatInteger(awards.length)} tone="success" />
          <StatCard label="Procurement Value" value={totalValue === null ? "Not disclosed" : `${formatInteger(totalValue)} mixed`} tone="warning" />
          <StatCard label="Web Evidence" value={formatInteger(data.webPages.length)} meta={`${data.duplicatesSkipped} duplicate pages skipped`} />
        </div>

        <div className="flex flex-wrap gap-2 rounded-[4px] border border-[#2A3441] bg-[#111111] p-3 text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">
          {[
            { id: "overview", label: "Overview" },
            { id: "indicators", label: "Procurement Indicators" },
            { id: "graph", label: "Relationship Graph" },
            { id: "timeline", label: "Timeline" },
            { id: "tables", label: "Tables" },
            { id: "sources", label: "Source Explorer" }
          ].map((section) => (
            <a className="rounded-[4px] border border-[#2A3441] px-3 py-2 transition hover:border-[#C58B2A] hover:text-[#E6E8EB]" href={`#${section.id}`} key={section.id}>
              {section.label}
            </a>
          ))}
        </div>

        <div id="overview">
          <Section eyebrow="Overview" title="Investigation Overview">
            <div className="grid gap-3 sm:grid-cols-2">
              <Metric label="Query" value={data.query} />
              <Metric label="Top buyer" value={topBuyer} />
              <Metric label="Procurement entities" value={formatInteger(procurementEvidence.length)} />
              <Metric label="Backend totals" value={data.dashboardSummary ? `${formatInteger(data.dashboardSummary.total_tenders)} tenders / ${formatInteger(data.dashboardSummary.total_companies)} companies` : "Not available"} />
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-3">
              <SummaryList title="Top Buyers" items={buyers.slice(0, 5).map((buyer) => `${buyer.name} (${buyer.records})`)} />
              <SummaryList title="Top Categories" items={categories.length ? categories.slice(0, 5).map((item) => `${item.name} (${item.count})`) : ["Not available"]} />
              <SummaryList title="Country Distribution" items={countries.length ? countries.slice(0, 5).map((item) => `${item.name} (${item.count})`) : ["Not available"]} />
            </div>
          </Section>
        </div>

        <div id="indicators">
          <Section eyebrow="Procurement" title="Procurement Indicators">
            {data.tenders.length === 0 && procurementEvidence.length === 0 ? (
              <EmptyState title="No procurement records found" message="The existing procurement APIs and extracted web evidence returned no procurement records for this query." />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {categories.slice(0, 6).map((item) => (
                  <button className={`rounded-[4px] border p-4 text-left transition hover:border-[#C58B2A] ${selectedSelection.kind === "indicator" && selectedSelection.id === `category:${item.name}` ? "border-[#C58B2A] bg-[#1F1A12]" : "border-[#2A3441] bg-[#171F2A]"}`} key={`category:${item.name}`} onClick={() => onSelectSelection({ kind: "indicator", id: `category:${item.name}`, label: item.name, meta: `${item.count} records` })} type="button">
                    <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">Category</div>
                    <div className="mt-2 text-sm font-semibold text-[#E6E8EB]">{item.name}</div>
                    <div className="mt-1 text-xs text-[#9AA4AF]">{item.count} matching records</div>
                  </button>
                ))}
                {countries.slice(0, 6).map((item) => (
                  <button className={`rounded-[4px] border p-4 text-left transition hover:border-[#C58B2A] ${selectedSelection.kind === "indicator" && selectedSelection.id === `country:${item.name}` ? "border-[#C58B2A] bg-[#1F1A12]" : "border-[#2A3441] bg-[#171F2A]"}`} key={`country:${item.name}`} onClick={() => onSelectSelection({ kind: "indicator", id: `country:${item.name}`, label: item.name, meta: `${item.count} records` })} type="button">
                    <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">Country</div>
                    <div className="mt-2 text-sm font-semibold text-[#E6E8EB]">{item.name}</div>
                    <div className="mt-1 text-xs text-[#9AA4AF]">{item.count} matching records</div>
                  </button>
                ))}
              </div>
            )}
          </Section>
        </div>

        <div id="graph">
          <Section eyebrow="Graph" title="Relationship Graph">
            {data.graph && data.graph.nodes.length > 0 ? (
              <div className="h-[760px] overflow-hidden rounded-[4px] border border-[#2A3441]">
                <RelationshipGraphExplorer graph={data.graph} onSelectionChange={(selection) => onSelectSelection(toWorkspaceSelection(selection))} showDetailsPanel={false} />
              </div>
            ) : (
              <EmptyState message="Graph data is unavailable from the existing graph API." />
            )}
          </Section>
        </div>

        <div id="timeline">
          <Section eyebrow="Timeline" title="Investigation Timeline">
            <Timeline
              items={steps.map((step) => ({
                detail: step.detail ?? (step.status === "pending" ? "Pending" : step.status === "running" ? "Running" : "Complete"),
                label: step.name,
                value: step.durationMs !== undefined ? `${step.durationMs} ms` : step.status === "pending" ? "Not started" : "Running"
              }))}
              onSelect={(item) => onSelectSelection({ kind: "timeline", id: item.label, label: item.label, meta: item.detail ?? item.value })}
              selectedKey={selectedSelection.kind === "timeline" ? selectedSelection.id : null}
            />
          </Section>
        </div>

        <div id="tables" className="space-y-5">
          <SearchableTenderTable onSelectSelection={onSelectSelection} selectedSelection={selectedSelection} tenders={data.tenders} />
          <SearchableAwardTable awards={awards} onSelectSelection={onSelectSelection} selectedSelection={selectedSelection} />
          <SearchableProcurementEvidenceTable evidence={procurementEvidence} onSelectSelection={onSelectSelection} pages={data.webPages} selectedSelection={selectedSelection} />
          <CanonicalCompanyTable companies={data.canonicalCompanies} onSelectSelection={onSelectSelection} selectedSelection={selectedSelection} />
          <BidHistoryTable />
          <SearchableBuyersTable buyers={buyers} onSelectSelection={onSelectSelection} selectedSelection={selectedSelection} />
          <SearchableWebTable onSelectSelection={onSelectSelection} pages={data.webPages} selectedSelection={selectedSelection} />
        </div>

        <div id="sources">
          <Section eyebrow="Sources" title="Source Explorer">
            {sources.length === 0 ? (
              <EmptyState message="No public web sources were discovered for this query." />
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {sources.map((source) => (
                  <SourceCard key={source.domain} onSelect={() => onSelectSelection({ kind: "source", id: source.domain, label: source.name, meta: source.domain })} source={source} />
                ))}
              </div>
            )}
          </Section>
        </div>

        <Section eyebrow="Network" title="Related Companies">
          {relatedCompanies.length === 0 ? (
            <EmptyState message="No related companies were returned by tender award details." />
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {relatedCompanies.map((company) => (
                <button className={`rounded-[4px] border p-4 text-left transition hover:border-[#C58B2A] ${selectedSelection.kind === "company" && selectedSelection.id === company.id ? "border-[#C58B2A] bg-[#1F1A12]" : "border-[#2A3441] bg-[#171F2A]"}`} key={company.id} onClick={() => onSelectSelection({ kind: "company", id: company.id, label: company.name, meta: company.registration_number ?? "No identifier" })} type="button">
                  <Users className="h-4 w-4 text-[#667A52]" aria-hidden="true" />
                  <div className="mt-2 text-sm font-semibold text-[#E6E8EB]">{company.name}</div>
                  <div className="mt-1 text-xs text-[#9AA4AF]">{company.registration_number ?? "No identifier"}</div>
                </button>
              ))}
            </div>
          )}
        </Section>
      </div>

      <aside className="space-y-5 xl:sticky xl:top-20 xl:h-[calc(100vh-5rem)] xl:overflow-y-auto">
        <WorkspaceInspector detail={selectionDetail} onSelectSelection={onSelectSelection} selectedSelection={selectedSelection} />
      </aside>
    </div>
  );
}

function SearchableTenderTable({
  tenders,
  onSelectSelection,
  selectedSelection
}: {
  tenders: TenderSummary[];
  onSelectSelection: (selection: WorkspaceSelection) => void;
  selectedSelection: WorkspaceSelection;
}) {
  const [filter, setFilter] = useState("");
  const items = filterItems(tenders, filter, (tender) => `${tender.title} ${tender.reference_number} ${tender.procuring_entity ?? ""}`);
  const columns: Column<TenderSummary>[] = [
    { key: "title", header: "Tender", render: (tender) => <RecordTitle title={tender.title} meta={tender.reference_number} /> },
    { key: "buyer", header: "Buyer", render: (tender) => <span>{tender.procuring_entity ?? "Unknown"}</span> },
    { key: "value", header: "Value", align: "right", render: (tender) => <span>{formatMoney(tender.estimated_value, tender.currency)} {tender.currency}</span> },
    { key: "published", header: "Published", render: (tender) => <span>{formatDate(tender.published_date)}</span> }
  ];
  return <WorkspaceTable title="Tender History" icon={<FileText className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState title="No procurement records found" message="No tenders match this investigation." />} items={items} onRowSelect={(tender) => onSelectSelection({ kind: "tender", id: tender.id, label: tender.title, meta: tender.reference_number ?? undefined })} selectedId={selectedSelection.kind === "tender" ? selectedSelection.id : null} /></WorkspaceTable>;
}

function SearchableAwardTable({
  awards,
  onSelectSelection,
  selectedSelection
}: {
  awards: Array<TenderDetail["awards"][number] & { tender: TenderDetail }>;
  onSelectSelection: (selection: WorkspaceSelection) => void;
  selectedSelection: WorkspaceSelection;
}) {
  const [filter, setFilter] = useState("");
  const items = filterItems(awards, filter, (award) => `${award.company.name} ${award.tender.title} ${award.currency}`);
  const columns: Column<(typeof awards)[number]>[] = [
    { key: "company", header: "Company", render: (award) => <RecordTitle title={award.company.name} meta={award.company.registration_number ?? "No identifier"} /> },
    { key: "tender", header: "Tender", render: (award) => <span>{award.tender.title}</span> },
    { key: "amount", header: "Award Value", align: "right", render: (award) => <span>{formatMoney(award.award_value, award.currency)} {award.currency}</span> },
    { key: "date", header: "Award Date", render: (award) => <span>{formatDate(award.award_date)}</span> }
  ];
  return <WorkspaceTable title="Award History" icon={<Award className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No award history is available from tender details." />} items={items} onRowSelect={(award) => onSelectSelection({ kind: "award", id: award.id, label: award.company.name, meta: award.tender.title })} selectedId={selectedSelection.kind === "award" ? selectedSelection.id : null} /></WorkspaceTable>;
}

function SearchableProcurementEvidenceTable({
  evidence,
  onSelectSelection,
  pages,
  selectedSelection
}: {
  evidence: ProcurementEvidence[];
  onSelectSelection: (selection: WorkspaceSelection) => void;
  pages: StoredWebPage[];
  selectedSelection: WorkspaceSelection;
}) {
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
  return <WorkspaceTable title="Procurement Evidence" icon={<Shield className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No procurement facts were extracted from web evidence." />} items={items} onRowSelect={(item) => onSelectSelection({ kind: "evidence", id: item.id, label: item.company_name ?? item.normalized_company_name ?? item.tender_title ?? "Evidence", meta: item.government_buyer ?? item.country ?? undefined })} selectedId={selectedSelection.kind === "evidence" ? selectedSelection.id : null} /></WorkspaceTable>;
}

function CanonicalCompanyTable({
  companies,
  onSelectSelection,
  selectedSelection
}: {
  companies: CanonicalCompany[];
  onSelectSelection: (selection: WorkspaceSelection) => void;
  selectedSelection: WorkspaceSelection;
}) {
  const [filter, setFilter] = useState("");
  const items = filterItems(companies, filter, (company) => `${company.canonical_name} ${company.aliases.join(" ")}`);
  const columns: Column<CanonicalCompany>[] = [
    { key: "name", header: "Canonical Name", render: (company) => <RecordTitle title={company.canonical_name} meta={`${company.linked_procurement_companies.length} procurement records`} /> },
    { key: "aliases", header: "Aliases", render: (company) => <span>{company.aliases.join(", ") || "None"}</span> },
    { key: "confidence", header: "Confidence", align: "right", render: (company) => <span>{formatPercent(company.confidence)}</span> },
    { key: "sources", header: "Linked Sources", render: (company) => <span>{company.matched_sources.length} sources / {company.linked_web_evidence.length} web evidence</span> }
  ];
  return <WorkspaceTable title="Canonical Entities" icon={<Users className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No canonical entity links were returned for this investigation." />} items={items} onRowSelect={(company) => onSelectSelection({ kind: "company", id: company.id, label: company.canonical_name, meta: company.confidence })} selectedId={selectedSelection.kind === "company" ? selectedSelection.id : null} /></WorkspaceTable>;
}

function SearchableBuyersTable({
  buyers,
  onSelectSelection,
  selectedSelection
}: {
  buyers: Array<{ id: string; name: string; records: number }>;
  onSelectSelection: (selection: WorkspaceSelection) => void;
  selectedSelection: WorkspaceSelection;
}) {
  const [filter, setFilter] = useState("");
  const items = filterItems(buyers, filter, (buyer) => buyer.name);
  const columns: Column<(typeof buyers)[number]>[] = [
    { key: "buyer", header: "Government Buyer", render: (buyer) => <span className="font-semibold">{buyer.name}</span> },
    { key: "records", header: "Records", align: "right", render: (buyer) => <span>{buyer.records}</span> },
    { key: "documents", header: "Documents", render: () => <span>Not available</span> }
  ];
  return <WorkspaceTable title="Government Buyers" icon={<Landmark className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No government buyers were returned by procurement records." />} items={items} onRowSelect={(buyer) => onSelectSelection({ kind: "buyer", id: buyer.id, label: buyer.name, meta: `${buyer.records} records` })} selectedId={selectedSelection.kind === "buyer" ? selectedSelection.id : null} /></WorkspaceTable>;
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

function SearchableWebTable({
  pages,
  onSelectSelection,
  selectedSelection
}: {
  pages: StoredWebPage[];
  onSelectSelection: (selection: WorkspaceSelection) => void;
  selectedSelection: WorkspaceSelection;
}) {
  const [filter, setFilter] = useState("");
  const items = filterItems(pages, filter, (page) => `${page.title ?? ""} ${page.source} ${page.url}`);
  const columns: Column<StoredWebPage>[] = [
    { key: "source", header: "Source", render: (page) => <RecordTitle title={page.title ?? page.source} meta={page.source} /> },
    { key: "url", header: "URL", render: (page) => <a className="break-all text-[#F3D59A] hover:underline" href={page.url} rel="noreferrer" target="_blank">{page.url}</a> },
    { key: "retrieved", header: "Retrieved", render: (page) => <span>{formatDate(page.retrieved_at)}</span> },
    { key: "entities", header: "Entities", align: "right", render: (page) => <span>{page.extraction.organization_names.length}</span> }
  ];
  return <WorkspaceTable title="Web Evidence" icon={<Globe2 className="h-4 w-4" />} filter={filter} onFilter={setFilter}><DataTable columns={columns} empty={<EmptyState message="No web evidence pages were stored for this query." />} items={items} onRowSelect={(page) => onSelectSelection({ kind: "document", id: page.id, label: page.title ?? page.source, meta: page.url })} selectedId={selectedSelection.kind === "document" ? selectedSelection.id : null} /></WorkspaceTable>;
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

function SourceCard({
  onSelect,
  source
}: {
  onSelect: () => void;
  source: { domain: string; name: string; records: number; documents: number; lastUpdate: string; executionTime: string };
}) {
  return (
    <button className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4 text-left transition hover:border-[#C58B2A]" onClick={onSelect} type="button">
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
    </button>
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

const RECENT_STORAGE_KEY = "sentry.investigation.recent";
const PINNED_STORAGE_KEY = "sentry.investigation.pinned";

function readInvestigationHistory(rawValue: string | null): InvestigationHistoryEntry[] {
  if (!rawValue) return [];

  try {
    const parsed = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const record = item as Partial<InvestigationHistoryEntry>;
        if (typeof record.query !== "string" || typeof record.label !== "string" || typeof record.updatedAt !== "string") return null;
        return { query: record.query, label: record.label, updatedAt: record.updatedAt };
      })
      .filter((item): item is InvestigationHistoryEntry => item !== null)
      .slice(0, 10);
  } catch {
    return [];
  }
}

function upsertInvestigationHistory(items: InvestigationHistoryEntry[], next: InvestigationHistoryEntry): InvestigationHistoryEntry[] {
  return [next, ...items.filter((item) => item.query !== next.query)].slice(0, 10);
}

function HistoryRail({
  items,
  onDelete,
  onSelect,
  onOpen,
  title
}: {
  items: InvestigationHistoryEntry[];
  onDelete: (query: string) => void;
  onOpen?: (query: string) => void;
  onSelect?: (query: string) => void;
  title: string;
}) {
  const openItem = onSelect ?? onOpen ?? (() => undefined);

  return (
    <Section eyebrow="Navigation" title={title}>
      {items.length === 0 ? (
        <EmptyState message={`No ${title.toLowerCase()} yet.`} />
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div className="flex items-stretch gap-2 rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-2" key={item.query}>
              <button className="min-w-0 flex-1 text-left" onClick={() => openItem(item.query)} type="button">
                <div className="truncate text-sm font-semibold text-[#E6E8EB]">{item.label}</div>
                <div className="mt-1 truncate text-xs text-[#9AA4AF]">{item.query}</div>
                <div className="mt-1 flex items-center gap-1 text-[11px] text-[#737373]">
                  <Clock3 className="h-3 w-3" />
                  {formatDate(item.updatedAt)}
                </div>
              </button>
              <button className="rounded-[4px] border border-[#2A3441] px-2 text-xs font-semibold text-[#9AA4AF] transition hover:border-[#C58B2A] hover:text-[#E6E8EB]" onClick={() => onDelete(item.query)} type="button">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function WorkspaceInspector({
  detail,
  onSelectSelection,
  selectedSelection
}: {
  detail: SelectionDetail;
  onSelectSelection: (selection: WorkspaceSelection) => void;
  selectedSelection: WorkspaceSelection;
}) {
  return (
    <SurfaceCard className="p-0">
      <div className="border-b border-[#2A3441] bg-[#171F2A]/45 px-4 py-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#9AA4AF]">
          <PanelRight className="h-4 w-4 text-[#C58B2A]" />
          Investigation Panel
        </div>
        <h2 className="mt-2 text-base font-semibold text-[#E6E8EB]">{detail.title}</h2>
        <p className="mt-1 text-xs text-[#9AA4AF]">{detail.summary}</p>
        <div className="mt-3 inline-flex rounded-[4px] border border-[#C58B2A] bg-[#2A2115] px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] text-[#F3D59A]">
          {detail.badge}
        </div>
      </div>
      <div className="space-y-5 p-4">
        <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9AA4AF]">Summary</div>
          <p className="mt-3 text-sm leading-6 text-[#E6E8EB]">{detail.summary}</p>
        </div>
        <SelectionDetailSection title="Properties" items={detail.properties} onSelectSelection={onSelectSelection} />
        <SelectionDetailSection title="Relationships" items={detail.relationships} onSelectSelection={onSelectSelection} />
        <SelectionDetailSection title="Evidence" items={detail.evidence} onSelectSelection={onSelectSelection} />
        <SelectionDetailSection title="Documents" items={detail.documents} onSelectSelection={onSelectSelection} />
        <SelectionDetailSection title="Timeline" items={detail.timeline} onSelectSelection={onSelectSelection} />
        <SelectionDetailSection title="Related Records" items={detail.relatedRecords} onSelectSelection={onSelectSelection} />
        <div className="rounded-[4px] border border-dashed border-[#2A3441] p-3 text-xs text-[#9AA4AF]">
          Current selection: {selectedSelection.label}
        </div>
      </div>
    </SurfaceCard>
  );
}

function SelectionDetailSection({
  items,
  onSelectSelection,
  title
}: {
  items: DetailItem[];
  onSelectSelection: (selection: WorkspaceSelection) => void;
  title: string;
}) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-[#C58B2A]">{title}</h3>
      {items.length === 0 ? (
        <div className="mt-3 rounded-[4px] border border-[#2A3441] bg-[#111111] p-3 text-sm text-[#9AA4AF]">No records available.</div>
      ) : (
        <div className="mt-3 divide-y divide-[#2A3441] rounded-[4px] border border-[#2A3441] bg-[#171F2A]">
          {items.map((item) =>
            item.target ? (
              (() => {
                const target = item.target;
                return (
              <button className="block w-full p-3 text-left transition hover:bg-[#1C2430]" key={`${item.label}-${item.value}`} onClick={() => onSelectSelection(target.selection)} type="button">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{item.label}</div>
                <div className="mt-1 text-sm text-[#E6E8EB]">{item.value}</div>
              </button>
                );
              })()
            ) : (
              <div className="p-3" key={`${item.label}-${item.value}`}>
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{item.label}</div>
                <div className="mt-1 text-sm text-[#E6E8EB]">{item.value}</div>
              </div>
            )
          )}
        </div>
      )}
    </section>
  );
}

function buildSelectionDetail({
  activeQuery,
  awards,
  buyers,
  categories,
  companyProfiles,
  countries,
  data,
  onSelectSelection,
  procurementEvidence,
  recentInvestigations,
  relatedCompanies,
  selectedSelection,
  sources,
  steps,
  topBuyer,
  totalValue
}: {
  activeQuery: string;
  awards: Array<TenderDetail["awards"][number] & { tender: TenderDetail }>;
  buyers: Array<{ id: string; name: string; records: number }>;
  categories: Array<{ name: string; count: number }>;
  companyProfiles: CompanyProfileCard[];
  countries: Array<{ name: string; count: number }>;
  data: InvestigationData;
  onSelectSelection: (selection: WorkspaceSelection) => void;
  procurementEvidence: ProcurementEvidence[];
  recentInvestigations: InvestigationHistoryEntry[];
  relatedCompanies: Array<{ id: string; name: string; registration_number: string | null; awards: number }>;
  selectedSelection: WorkspaceSelection;
  sources: Array<{ domain: string; name: string; records: number; documents: number; lastUpdate: string; executionTime: string }>;
  steps: InvestigationStep[];
  topBuyer: string;
  totalValue: number | null;
}): SelectionDetail {
  const base = {
    badge: "Investigation",
    documents: [] as DetailItem[],
    evidence: [] as DetailItem[],
    properties: [] as DetailItem[],
    relatedRecords: [] as DetailItem[],
    relationships: [] as DetailItem[],
    summary: `Active investigation for ${activeQuery}.`,
    timeline: [] as DetailItem[],
    title: selectedSelection.label
  };

  const makeTarget = (kind: WorkspaceSelectionKind, id: string, label: string, meta?: string): SelectionTarget => ({ selection: { kind, id, label, meta }, label });
  const makeItem = (label: string, value: string, target?: SelectionTarget): DetailItem => ({ label, value, target });

  if (selectedSelection.kind === "company") {
    const company = companyProfiles.find((item) => item.id === selectedSelection.id);
    const relatedCompany = relatedCompanies.find((item) => item.id === selectedSelection.id);
    const matchingEvidence = procurementEvidence.filter((item) => item.company_name?.toLowerCase().includes(selectedSelection.label.toLowerCase()) || item.normalized_company_name?.toLowerCase().includes(selectedSelection.label.toLowerCase()));
    return {
      ...base,
      badge: "Company",
      summary: `${(company?.awards ?? relatedCompany?.awards ?? 0)} awards and ${matchingEvidence.length} evidence records linked to this company.`,
      properties: [
        makeItem("Company", selectedSelection.label),
        makeItem("Identifier", company?.registration_number ?? relatedCompany?.registration_number ?? selectedSelection.meta ?? "Not available"),
        makeItem("Awards", formatInteger(company?.awards ?? relatedCompany?.awards ?? 0)),
        makeItem("Confidence", company?.confidence ? formatPercent(company.confidence) : "Not available")
      ],
      relationships: relatedCompanies
        .filter((item) => item.id !== selectedSelection.id)
        .slice(0, 5)
        .map((item) => makeItem(item.name, `${item.awards} awards`, makeTarget("company", item.id, item.name, item.registration_number ?? undefined))),
      evidence: matchingEvidence.slice(0, 5).map((item) => makeItem(item.tender_title ?? item.contract_title ?? item.company_name ?? "Evidence", item.contract_number ?? item.tender_number ?? item.country ?? "Evidence record", makeTarget("evidence", item.id, item.company_name ?? item.normalized_company_name ?? item.id, item.government_buyer ?? undefined))),
      documents: data.webPages.filter((page) => page.procurement_evidence?.company_id === selectedSelection.id).slice(0, 4).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
      timeline: steps.slice(0, 4).map((step) => makeItem(step.name, step.detail ?? step.status, makeTarget("timeline", step.name, step.name, step.detail ?? step.status))),
      relatedRecords: data.tenders.slice(0, 5).map((tender) => makeItem(tender.title, tender.reference_number, makeTarget("tender", tender.id, tender.title, tender.reference_number)))
    };
  }

  if (selectedSelection.kind === "tender") {
    const tender = data.tenders.find((item) => item.id === selectedSelection.id);
    const tenderDetail = data.tenderDetails.find((item) => item.id === selectedSelection.id);
    const tenderAwards = awards.filter((award) => award.tender.id === selectedSelection.id || award.tender.title === tender?.title);
    return {
      ...base,
      badge: "Tender",
      summary: `${tenderAwards.length} awards and ${tenderDetail?.participating_companies.length ?? 0} participating companies attached to this tender.`,
      properties: [
        makeItem("Reference", tender?.reference_number ?? selectedSelection.meta ?? "Not available"),
        makeItem("Buyer", tender?.procuring_entity ?? tenderDetail?.buyer.name ?? topBuyer),
        makeItem("Estimated value", tender ? `${formatMoney(tender.estimated_value, tender.currency)} ${tender.currency}` : "Not available"),
        makeItem("Published", formatDate(tender?.published_date ?? null)),
        makeItem("Closing", formatDate(tender?.closing_date ?? null))
      ],
      relationships: tenderAwards.slice(0, 5).map((award) => makeItem(award.company.name, `${formatMoney(award.award_value, award.currency)} ${award.currency}`, makeTarget("award", award.id, award.company.name, award.tender.title))),
      evidence: procurementEvidence.filter((item) => item.tender_id === selectedSelection.id).slice(0, 5).map((item) => makeItem(item.company_name ?? item.normalized_company_name ?? item.tender_title ?? "Evidence", item.government_buyer ?? item.country ?? "Evidence record", makeTarget("evidence", item.id, item.company_name ?? item.normalized_company_name ?? item.id, item.government_buyer ?? undefined))),
      documents: data.webPages.filter((page) => page.procurement_evidence?.tender_id === selectedSelection.id || page.procurement_evidence?.tender_title === tender?.title).slice(0, 4).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
      timeline: [
        makeItem("Published", formatDate(tender?.published_date ?? null), makeTarget("timeline", "published", "Published", formatDate(tender?.published_date ?? null))),
        makeItem("Closing", formatDate(tender?.closing_date ?? null), makeTarget("timeline", "closing", "Closing", formatDate(tender?.closing_date ?? null))),
        makeItem("Updated", formatDate(tender?.updated_at ?? null), makeTarget("timeline", "updated", "Updated", formatDate(tender?.updated_at ?? null)))
      ],
      relatedRecords: tenderDetail?.participating_companies.slice(0, 5).map((company) => makeItem(company.name, company.registration_number ?? "No identifier", makeTarget("company", company.id, company.name, company.registration_number ?? undefined))) ?? []
    };
  }

  if (selectedSelection.kind === "buyer") {
    const buyer = buyers.find((item) => item.id === selectedSelection.id);
    const relatedTenders = data.tenders.filter((item) => (item.procuring_entity ?? "").toLowerCase() === selectedSelection.id);
    return {
      ...base,
      badge: "Buyer",
      summary: `${buyer?.records ?? 0} records are associated with this buyer in the current investigation.`,
      properties: [makeItem("Buyer", selectedSelection.label), makeItem("Records", formatInteger(buyer?.records ?? 0)), makeItem("Evidence pages", formatInteger(procurementEvidence.filter((item) => item.government_buyer?.toLowerCase() === selectedSelection.id).length))],
      relationships: relatedTenders.slice(0, 5).map((tender) => makeItem(tender.title, tender.reference_number, makeTarget("tender", tender.id, tender.title, tender.reference_number))),
      evidence: procurementEvidence.filter((item) => item.government_buyer?.toLowerCase() === selectedSelection.id).slice(0, 5).map((item) => makeItem(item.tender_title ?? item.contract_title ?? "Evidence", item.country ?? item.procurement_sector ?? "Evidence record", makeTarget("evidence", item.id, item.tender_title ?? item.contract_title ?? item.id, item.country ?? undefined))),
      documents: data.webPages.filter((page) => page.extraction.government_entities.some((entity) => entity.toLowerCase().includes(selectedSelection.id))).slice(0, 4).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
      timeline: steps.slice(0, 4).map((step) => makeItem(step.name, step.status, makeTarget("timeline", step.name, step.name, step.status))),
      relatedRecords: relatedTenders.slice(0, 5).map((tender) => makeItem(tender.title, tender.reference_number, makeTarget("tender", tender.id, tender.title, tender.reference_number)))
    };
  }

  if (selectedSelection.kind === "evidence") {
    const evidence = procurementEvidence.find((item) => item.id === selectedSelection.id);
    const page = data.webPages.find((item) => item.procurement_evidence?.id === selectedSelection.id);
    return {
      ...base,
      badge: "Evidence",
      summary: evidence ? `${evidence.tender_title ?? evidence.contract_title ?? "Evidence record"} from ${evidence.government_buyer ?? evidence.country ?? "unknown source"}.` : base.summary,
      properties: [
        makeItem("Company", evidence?.company_name ?? evidence?.normalized_company_name ?? "Not available"),
        makeItem("Buyer", evidence?.government_buyer ?? "Not available"),
        makeItem("Country", evidence?.country ?? "Not available"),
        makeItem("Sector", evidence?.procurement_sector ?? evidence?.tender_category ?? "Not available"),
        makeItem("Value", evidence?.contract_value ? `${formatMoney(evidence.contract_value, evidence.currency ?? "")} ${evidence.currency ?? ""}` : "Not available")
      ],
      relationships: [
        evidence?.tender_id ? makeItem("Tender", evidence.tender_id, makeTarget("tender", evidence.tender_id, evidence.tender_title ?? evidence.tender_id, evidence.tender_number ?? undefined)) : null,
        evidence?.company_id ? makeItem("Company", evidence.company_id, makeTarget("company", evidence.company_id, evidence.company_name ?? evidence.company_id, evidence.company_name ?? undefined)) : null
      ].filter((item): item is DetailItem => item !== null),
      evidence: page ? [makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))] : [],
      documents: page ? [makeItem(page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))] : [],
      timeline: [makeItem("Publication", formatDate(evidence?.publication_date ?? null)), makeItem("Award", formatDate(evidence?.award_date ?? null))],
      relatedRecords: [
        ...(evidence?.tender_id ? [makeItem("Tender", evidence.tender_id, makeTarget("tender", evidence.tender_id, evidence.tender_title ?? evidence.tender_id, evidence.tender_number ?? undefined))] : []),
        ...(evidence?.company_id ? [makeItem("Company", evidence.company_id, makeTarget("company", evidence.company_id, evidence.company_name ?? evidence.company_id, evidence.company_name ?? undefined))] : [])
      ]
    };
  }

  if (selectedSelection.kind === "document" || selectedSelection.kind === "source") {
    const page = data.webPages.find((item) => item.id === selectedSelection.id);
    return {
      ...base,
      badge: selectedSelection.kind === "document" ? "Document" : "Source",
      summary: page ? `${page.source} captured on ${formatDate(page.retrieved_at)}.` : base.summary,
      properties: page
        ? [
            makeItem("Source", page.source),
            makeItem("Title", page.title ?? "Not available"),
            makeItem("URL", page.url),
            makeItem("Retrieved", formatDate(page.retrieved_at)),
            makeItem("Evidence extracted", page.procurement_evidence ? "Yes" : "No")
          ]
        : [makeItem("Source", selectedSelection.meta ?? "Not available")],
      relationships: page?.procurement_evidence ? [makeItem("Evidence", page.procurement_evidence.id, makeTarget("evidence", page.procurement_evidence.id, page.procurement_evidence.tender_title ?? page.procurement_evidence.contract_title ?? page.procurement_evidence.id, page.procurement_evidence.government_buyer ?? undefined))] : [],
      evidence: page?.procurement_evidence ? [makeItem(page.procurement_evidence.tender_title ?? page.procurement_evidence.contract_title ?? "Evidence", page.procurement_evidence.government_buyer ?? "Procurement evidence", makeTarget("evidence", page.procurement_evidence.id, page.procurement_evidence.company_name ?? page.procurement_evidence.id, page.procurement_evidence.government_buyer ?? undefined))] : [],
      documents: page ? [makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))] : [],
      timeline: page ? [makeItem("Retrieved", formatDate(page.retrieved_at))] : [],
      relatedRecords: page?.procurement_evidence
        ? [makeItem("Related evidence", page.procurement_evidence.id, makeTarget("evidence", page.procurement_evidence.id, page.procurement_evidence.tender_title ?? page.procurement_evidence.id, page.procurement_evidence.government_buyer ?? undefined))]
        : []
    };
  }

  if (selectedSelection.kind === "timeline") {
    const step = steps.find((item) => item.name === selectedSelection.id);
    return {
      ...base,
      badge: "Timeline",
      summary: step ? `${step.name} is currently ${step.status}.` : base.summary,
      properties: [makeItem("Step", step?.name ?? selectedSelection.label), makeItem("Status", step?.status ?? "Not available"), makeItem("Duration", step?.durationMs !== undefined ? `${step.durationMs} ms` : "Not available"), makeItem("Records", step?.recordsFound !== undefined ? formatInteger(step.recordsFound) : "Not available")],
      relationships: data.tenders.slice(0, 3).map((tender) => makeItem(tender.title, tender.reference_number, makeTarget("tender", tender.id, tender.title, tender.reference_number))),
      evidence: procurementEvidence.slice(0, 4).map((item) => makeItem(item.tender_title ?? item.contract_title ?? "Evidence", item.government_buyer ?? item.country ?? "Evidence record", makeTarget("evidence", item.id, item.tender_title ?? item.contract_title ?? item.id, item.government_buyer ?? undefined))),
      documents: data.webPages.slice(0, 4).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
      timeline: steps.map((item) => makeItem(item.name, item.status, makeTarget("timeline", item.name, item.name, item.status))),
      relatedRecords: sources.slice(0, 4).map((source) => makeItem(source.name, source.domain, makeTarget("source", source.domain, source.name, source.domain)))
    };
  }

  if (selectedSelection.kind === "indicator") {
    const [dimension, value] = selectedSelection.id.split(":", 2);
    const count = dimension === "category" ? categories.find((item) => item.name === value)?.count : countries.find((item) => item.name === value)?.count;
    const matchingEvidence = procurementEvidence.filter((item) => (dimension === "category" ? item.procurement_sector ?? item.tender_category : item.country) === value);
    return {
      ...base,
      badge: "Indicator",
      summary: `${count ?? 0} records match this procurement indicator.`,
      properties: [makeItem("Indicator", selectedSelection.label), makeItem("Dimension", dimension), makeItem("Matches", formatInteger(count ?? 0))],
      relationships: matchingEvidence.slice(0, 5).map((item) => makeItem(item.tender_title ?? item.contract_title ?? "Evidence", item.government_buyer ?? item.country ?? "Indicator evidence", makeTarget("evidence", item.id, item.company_name ?? item.id, item.government_buyer ?? undefined))),
      evidence: matchingEvidence.slice(0, 5).map((item) => makeItem(item.company_name ?? item.normalized_company_name ?? item.id, item.government_buyer ?? item.country ?? "Indicator evidence", makeTarget("evidence", item.id, item.company_name ?? item.id, item.government_buyer ?? undefined))),
      documents: data.webPages.filter((page) => page.procurement_evidence && matchingEvidence.some((item) => item.id === page.procurement_evidence?.id)).slice(0, 4).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
      timeline: steps.slice(0, 4).map((step) => makeItem(step.name, step.status, makeTarget("timeline", step.name, step.name, step.status))),
      relatedRecords: matchingEvidence.slice(0, 5).map((item) => makeItem(item.tender_title ?? item.contract_title ?? item.company_name ?? "Evidence", item.contract_number ?? item.tender_number ?? item.country ?? "Evidence record", makeTarget("evidence", item.id, item.company_name ?? item.id, item.government_buyer ?? undefined)))
    };
  }

  if (selectedSelection.kind === "graph-node" || selectedSelection.kind === "graph-edge") {
    const graph = data.graph;
    if (graph) {
      if (selectedSelection.kind === "graph-node") {
        const node = graph.nodes.find((item) => item.id === selectedSelection.id);
        const connectedEdges = graph.edges.filter((edge) => edge.source === selectedSelection.id || edge.target === selectedSelection.id);
        return {
          ...base,
          badge: "Graph Node",
          summary: node ? `${node.label} with ${connectedEdges.length} connected relationships.` : base.summary,
          properties: node ? [makeItem("Type", node.type), makeItem("Label", node.label), makeItem("Node id", node.id), ...Object.entries(node.data).slice(0, 4).map(([key, value]) => makeItem(key.replaceAll("_", " "), displayValue(value)))] : [makeItem("Node", selectedSelection.id)],
          relationships: connectedEdges.slice(0, 5).map((edge) => makeItem(edge.label, `${edge.source} -> ${edge.target}`, makeTarget("graph-edge", edge.id, edge.label, `${edge.source} -> ${edge.target}`))),
          evidence: connectedEdges.slice(0, 5).map((edge) => makeItem(edge.label, `${edge.source} -> ${edge.target}`)),
          documents: data.webPages.slice(0, 3).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
          timeline: steps.slice(0, 4).map((step) => makeItem(step.name, step.status, makeTarget("timeline", step.name, step.name, step.status))),
          relatedRecords: graph.nodes.filter((item) => item.id !== selectedSelection.id).slice(0, 6).map((item) => makeItem(item.label, item.type, makeTarget("graph-node", item.id, item.label, item.type)))
        };
      }

      const edge = graph.edges.find((item) => item.id === selectedSelection.id);
      return {
        ...base,
        badge: "Graph Relationship",
        summary: edge ? `${edge.label} between ${edge.source} and ${edge.target}.` : base.summary,
        properties: edge ? [makeItem("Relationship", edge.label), makeItem("Source", edge.source), makeItem("Target", edge.target), ...Object.entries(edge.data).slice(0, 4).map(([key, value]) => makeItem(key.replaceAll("_", " "), displayValue(value)))] : [makeItem("Edge", selectedSelection.id)],
        relationships: edge ? [makeItem(edge.source, edge.source, makeTarget("graph-node", edge.source, edge.source)), makeItem(edge.target, edge.target, makeTarget("graph-node", edge.target, edge.target))] : [],
        evidence: edge ? [makeItem(edge.label, `${edge.source} -> ${edge.target}`)] : [],
        documents: data.webPages.slice(0, 3).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
        timeline: steps.slice(0, 4).map((step) => makeItem(step.name, step.status, makeTarget("timeline", step.name, step.name, step.status))),
        relatedRecords: graph.nodes.filter((item) => item.id !== selectedSelection.id).slice(0, 6).map((item) => makeItem(item.label, item.type, makeTarget("graph-node", item.id, item.label, item.type)))
      };
    }
  }

  return {
    ...base,
    summary: `Investigation overview for ${activeQuery}.`,
    properties: [
      makeItem("Query", activeQuery),
      makeItem("Tenders", formatInteger(data.tenders.length)),
      makeItem("Companies", formatInteger(data.companies.length)),
      makeItem("Evidence pages", formatInteger(data.webPages.length)),
      makeItem("Awards", formatInteger(awards.length)),
      makeItem("Procurement value", totalValue === null ? "Not disclosed" : `${formatInteger(totalValue)} mixed`)
    ],
    relationships: [
      buyers[0] ? makeItem("Top buyer", buyers[0].name, makeTarget("buyer", buyers[0].id, buyers[0].name, `${buyers[0].records} records`)) : null,
      data.tenders[0] ? makeItem("Primary tender", data.tenders[0].title, makeTarget("tender", data.tenders[0].id, data.tenders[0].title, data.tenders[0].reference_number)) : null,
      companyProfiles[0] ? makeItem("Primary company", companyProfiles[0].name, makeTarget("company", companyProfiles[0].id, companyProfiles[0].name, companyProfiles[0].registration_number ?? undefined)) : null
    ].filter((item): item is DetailItem => item !== null),
    evidence: procurementEvidence.slice(0, 5).map((item) => makeItem(item.tender_title ?? item.contract_title ?? item.company_name ?? "Evidence", item.government_buyer ?? item.country ?? "Evidence record", makeTarget("evidence", item.id, item.company_name ?? item.id, item.government_buyer ?? undefined))),
    documents: data.webPages.slice(0, 5).map((page) => makeItem(page.title ?? page.source, page.url, makeTarget("document", page.id, page.title ?? page.source, page.url))),
    timeline: steps.map((step) => makeItem(step.name, step.detail ?? step.status, makeTarget("timeline", step.name, step.name, step.detail ?? step.status))),
    relatedRecords: [
      ...sources.slice(0, 3).map((source) => makeItem(source.name, source.domain, makeTarget("source", source.domain, source.name, source.domain))),
      ...recentInvestigations.slice(0, 3).map((item) => makeItem(item.label, item.query, makeTarget("overview", item.query, item.label, item.query)))
    ]
  };
}

function toWorkspaceSelection(selection: RelationshipGraphSelection): WorkspaceSelection {
  if (!selection) {
    return { kind: "overview", id: "overview", label: "Investigation overview" };
  }

  if (selection.kind === "node") {
    return {
      kind: "graph-node",
      id: selection.node.id,
      label: selection.node.label,
      meta: selection.node.type
    };
  }

  return {
    kind: "graph-edge",
    id: selection.edge.id,
    label: selection.edge.label,
    meta: `${selection.edge.source} -> ${selection.edge.target}`
  };
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "Not available";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => displayValue(item)).join(", ") || "Not available";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
