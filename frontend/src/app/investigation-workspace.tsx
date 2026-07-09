"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Award,
  Building2,
  Check,
  ChevronRight,
  ExternalLink,
  FileText,
  Gauge,
  Globe2,
  Lightbulb,
  Loader2,
  Maximize2,
  Network,
  Search,
  X
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { RelationshipGraphExplorer } from "@/app/graph/relationship-graph";
import { CommandCenter } from "@/app/command-center";
import { EntitySearch, type PinnedEntity } from "@/components/search/entity-search";
import { EvidenceCard, type EvidenceItem } from "@/components/intel/evidence-card";
import { AiInvestigationPanel } from "@/components/intel/ai-investigation-panel";
import { AnalystReportSections } from "@/components/intel/analyst-report";
import { AnalystTrace } from "@/components/intel/analyst-trace";
import { EvidenceLedger } from "@/components/intel/evidence-ledger";
import { GroundingCard } from "@/components/intel/grounding-card";
import { AiMemory } from "@/components/intel/ai-memory";
import { ProviderBadge } from "@/components/intel/provider-badge";
import { Section, StatCard } from "@/components/ui/card";
import { PageShell, SeverityBadge } from "@/components/ui/page";
import { EmptyState, ErrorState, SkeletonBlock } from "@/components/ui/states";
import { Timeline, type TimelineItem } from "@/components/ui/timeline";
import {
  getLLMProviders,
  getProcurementEvidence,
  searchWebEvidence,
  streamInvestigation,
  type EntityResolutionResult,
  type InvestigationPackage,
  type InvestigationReasoning,
  type InvestigationStreamStep,
  type LLMProviderStatus,
  type ReasoningFinding,
  type RelationshipGraph,
  type StoredWebPage
} from "@/lib/api";
import { bySourcePriority } from "@/lib/sources";
import { formatCompactMoney, formatDate, formatMoneyFull } from "@/lib/format";

/* ============================================================ pipeline */

type StepStatus = "pending" | "running" | "complete" | "error";
type Step = { key: string; name: string; status: StepStatus; detail?: string };

// Mirrors the backend SSE step keys emitted by /api/investigations/stream.
const STEP_TEMPLATE: Step[] = [
  { key: "plan", name: "Understand request & select sources", status: "pending" },
  { key: "retrieve", name: "Retrieve procurement records", status: "pending" },
  { key: "resolve", name: "Resolve entities", status: "pending" },
  { key: "indicators", name: "Run risk engine", status: "pending" },
  { key: "reasoning", name: "Reason & generate findings", status: "pending" }
];

/* ============================================================ root */

export function InvestigationWorkspace({ initialQuery }: { initialQuery: string }) {
  const router = useRouter();
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [steps, setSteps] = useState<Step[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pkg, setPkg] = useState<InvestigationPackage | null>(null);
  const [reasoning, setReasoning] = useState<InvestigationReasoning | null>(null);
  const [graph, setGraph] = useState<RelationshipGraph | null>(null);
  const [resolution, setResolution] = useState<EntityResolutionResult | null>(null);
  const [webPages, setWebPages] = useState<StoredWebPage[]>([]);
  const [webBusy, setWebBusy] = useState(false);
  const [processingMs, setProcessingMs] = useState<number | null>(null);
  const [providerStatus, setProviderStatus] = useState<LLMProviderStatus | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const startedAtRef = useRef<number | null>(null);

  // Live provider status for the workspace badge (item 7).
  useEffect(() => {
    getLLMProviders()
      .then(setProviderStatus)
      .catch(() => undefined);
  }, []);

  const runInvestigation = useCallback((query: string) => {
    // Cancel any in-flight investigation before starting a new one.
    abortRef.current?.();

    setRunning(true);
    setError(null);
    setPkg(null);
    setReasoning(null);
    setGraph(null);
    setResolution(null);
    setWebPages([]);
    setProcessingMs(null);
    startedAtRef.current = performance.now();
    setSteps(STEP_TEMPLATE.map((s) => ({ ...s })));

    const applyStep = (evt: InvestigationStreamStep) => {
      setSteps((prev) => {
        const next = prev.some((s) => s.key === evt.key)
          ? prev.map((s) => (s.key === evt.key ? { ...s, status: evt.status, detail: evt.detail ?? s.detail } : s))
          : [...prev, { key: evt.key, name: evt.label, status: evt.status, detail: evt.detail }];
        return next;
      });
    };

    abortRef.current = streamInvestigation(query, {
      onStep: applyStep,
      onCandidates: (res) => setResolution(res),
      onReport: (report) => {
        if (startedAtRef.current != null) setProcessingMs(performance.now() - startedAtRef.current);
        setPkg(report.package);
        setReasoning(report.reasoning);
        // Consume the backend-generated graph exactly as returned. The package
        // graph is the single source of truth (tenders, buyers, companies,
        // awards, evidence, indicators, documents); never rebuild it here.
        setGraph(report.package.graph);
        // The report package also carries the final resolved entities.
        if (report.package.resolved_entities) setResolution(report.package.resolved_entities);
        setRunning(false);
        // best-effort: pull already-stored web procurement evidence (DB, fast)
        getProcurementEvidence(query, 12)
          .then((r) => setWebPages(r.items))
          .catch(() => undefined);
      },
      onError: (message) => {
        setError(message);
        setRunning(false);
        setSteps((prev) => prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s)));
      }
    });
  }, []);

  useEffect(() => {
    if (initialQuery) {
      setActiveQuery(initialQuery);
      runInvestigation(initialQuery);
    }
    return () => abortRef.current?.();
  }, [initialQuery, runInvestigation]);

  // Investigations start ONLY from a verified, selected canonical entity — never
  // from arbitrary free text. The entity-search component enforces selection;
  // this runs the existing pipeline on the locked entity's canonical name.
  const investigateEntity = useCallback(
    (entity: PinnedEntity) => {
      const query = entity.canonical_name;
      setActiveQuery(query);
      router.push(`/?q=${encodeURIComponent(query)}`);
      runInvestigation(query);
    },
    [router, runInvestigation]
  );

  const launchFollowUp = useCallback(
    (query: string) => {
      setActiveQuery(query);
      router.push(`/?q=${encodeURIComponent(query)}`);
      runInvestigation(query);
    },
    [router, runInvestigation]
  );

  function reset() {
    abortRef.current?.();
    setActiveQuery("");
    setPkg(null);
    setReasoning(null);
    setGraph(null);
    setResolution(null);
    setSteps([]);
    setWebPages([]);
    setProcessingMs(null);
    setError(null);
    router.push("/");
  }

  async function runWebSearch() {
    if (!activeQuery) return;
    setWebBusy(true);
    try {
      const res = await searchWebEvidence(activeQuery);
      setWebPages(res.stored_pages.length ? res.stored_pages : webPages);
    } catch {
      /* tolerate */
    } finally {
      setWebBusy(false);
    }
  }

  return (
    <PageShell>
      <EntitySearch
        running={running}
        activeQuery={activeQuery}
        onInvestigate={investigateEntity}
        onReset={reset}
        providerBadge={
          providerStatus ? (
            <ProviderBadge
              generatedBy={providerStatus.mode === "llm" ? "llm" : "deterministic"}
              provider={providerStatus.providers[0]}
            />
          ) : null
        }
      />

      {(running || steps.length > 0) && steps.some((s) => s.status !== "pending") && (
        <PipelineStrip steps={steps} running={running} />
      )}

      {error && !running && (
        <div className="mt-6">
          <ErrorState message={error} title="Investigation could not complete" />
        </div>
      )}

      {!activeQuery && !running && <CommandCenter />}

      {reasoning && !running && (
        <InvestigationResults
          query={activeQuery}
          pkg={pkg}
          reasoning={reasoning}
          graph={graph}
          resolution={resolution}
          webPages={webPages}
          onWebSearch={runWebSearch}
          webBusy={webBusy}
          onFollowUp={launchFollowUp}
          processingMs={processingMs}
        />
      )}
    </PageShell>
  );
}

/* ============================================================ pipeline strip */

function PipelineStrip({ steps, running }: { steps: Step[]; running: boolean }) {
  const done = steps.filter((s) => s.status === "complete").length;
  const pct = steps.length ? Math.round((done / steps.length) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="mt-6 overflow-hidden rounded-[18px] border border-border bg-surface/80 elevate"
    >
      {/* console header with live progress */}
      <div className="flex items-center gap-3 border-b border-border bg-bg-2/50 px-5 py-3">
        <span className="relative grid h-7 w-7 place-items-center rounded-md border border-accent/30 bg-accent/[0.08] text-accent">
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold text-text">
            {running ? "Investigation in progress" : "Investigation complete"}
          </div>
          <div className="text-[11px] text-faint">
            {running ? "The agent is retrieving records, resolving entities and scoring risk in real time." : "Full evidence trace assembled."}
          </div>
        </div>
        <span className="tabular text-sm font-semibold text-accent">{pct}%</span>
      </div>
      {/* progress rail */}
      <div className="h-0.5 w-full bg-border">
        <motion.div
          className="h-full bg-accent"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>

      {/* live vertical trace */}
      <div className="relative px-5 py-4">
        {/* connector spine */}
        <span className="absolute bottom-6 left-[30px] top-6 w-px bg-border" aria-hidden />
        <ol>
        {steps.map((s, i) => (
          <motion.li
            key={s.key}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="relative flex items-start gap-3 py-1.5"
          >
            <span
              className={`relative z-10 grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 transition-colors ${
                s.status === "complete"
                  ? "border-success/50 bg-success/15 text-success"
                  : s.status === "running"
                    ? "border-accent/60 bg-accent/15 text-accent"
                    : s.status === "error"
                      ? "border-danger/50 bg-danger/15 text-danger"
                      : "border-border bg-surface text-faint"
              }`}
            >
              {s.status === "complete" ? (
                <Check className="h-3 w-3" />
              ) : s.status === "running" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : s.status === "error" ? (
                <X className="h-3 w-3" />
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
              )}
              {s.status === "running" && (
                <span className="absolute inset-0 rounded-full border-2 border-accent/40 pulse-live" />
              )}
            </span>
            <div className="min-w-0 flex-1 pt-0.5">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium ${s.status === "pending" ? "text-faint" : "text-text"}`}>
                  {s.name}
                </span>
                {s.status === "running" && (
                  <span className="rounded-full bg-accent/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">
                    live
                  </span>
                )}
              </div>
              <AnimatePresence mode="wait">
                <motion.div
                  key={s.detail ?? s.status}
                  initial={{ opacity: 0, y: 2 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[11px] text-faint"
                >
                  {s.detail ?? (s.status === "running" ? "Working…" : s.status === "complete" ? "Done" : "Queued")}
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.li>
        ))}
        </ol>
      </div>
    </motion.div>
  );
}

/* ============================================================ investigation results */

function InvestigationResults({
  query,
  pkg,
  reasoning,
  graph,
  resolution,
  webPages,
  onWebSearch,
  webBusy,
  onFollowUp,
  processingMs
}: {
  query: string;
  pkg: InvestigationPackage | null;
  reasoning: InvestigationReasoning;
  graph: RelationshipGraph | null;
  resolution: EntityResolutionResult | null;
  webPages: StoredWebPage[];
  onWebSearch: () => void;
  webBusy: boolean;
  onFollowUp: (query: string) => void;
  processingMs: number | null;
}) {
  const [fullGraphOpen, setFullGraphOpen] = useState(false);
  const awards = useMemo(() => pkg?.records.flatMap((r) => r.awards) ?? [], [pkg]);
  const awardedValue = useMemo(() => awards.reduce((s, a) => s + (Number(a.award_value) || 0), 0), [awards]);

  // Indian procurement sources first everywhere records are listed (item 8).
  const orderedRecords = useMemo(
    () => bySourcePriority(pkg?.records ?? [], (r) => r.tender.metadata?.source_name),
    [pkg]
  );

  const timelineItems: TimelineItem[] = (pkg?.timeline ?? []).slice(0, 14).map((e) => ({
    label: e.label,
    value: formatDate(e.event_date),
    detail: e.source_name,
    tone: e.label.startsWith("Award") ? "success" : e.label.includes("closing") ? "warning" : "accent"
  }));

  const hasRecords = (pkg?.records.length ?? 0) > 0;

  // Node-type breakdown of the backend graph. Rendered so an analyst can confirm
  // the graph faithfully represents the package (evidence/indicator/company/
  // buyer/award nodes all present) and the counts match the backend exactly.
  const graphStats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const n of graph?.nodes ?? []) counts[n.type] = (counts[n.type] ?? 0) + 1;
    return counts;
  }, [graph]);

  useEffect(() => {
    if (!fullGraphOpen) return;

    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, [fullGraphOpen]);

  return (
    <div className="mt-6 space-y-5">
      {/* Canonical entity resolution — never silently ignore backend candidates. */}
      {resolution && resolution.candidates.length > 0 && (
        <EntityCandidatesPanel resolution={resolution} onSelect={onFollowUp} />
      )}

      {/* Prior related investigations (AI memory) surface even without records */}
      {reasoning.prior_investigations.length > 0 && !hasRecords && (
        <Section eyebrow="AI memory" title="Previous related investigations">
          <AiMemory hits={reasoning.prior_investigations} onReuse={onFollowUp} />
        </Section>
      )}

      {!hasRecords ? (
        <EmptyState
          icon={<Search className="h-5 w-5" />}
          title="Insufficient evidence"
          message={`“${query}” did not match any imported tenders, companies, buyers, or awards. Import the entity or connect a source to investigate it.`}
        />
      ) : (
        <>
          {/* graph first: the relationship network is the primary investigation surface */}
          <Section
            eyebrow="Network"
            title="Investigation graph"
            action={
              <div className="flex items-center gap-2">
                <span className="hidden items-center gap-1.5 text-xs text-faint sm:inline-flex">
                  <Network className="h-3.5 w-3.5" />
                  {graph?.nodes.length ?? 0} nodes | {graph?.edges.length ?? 0} relationships
                </span>
                {Object.keys(graphStats).length > 0 && (
                  <span className="hidden flex-wrap items-center gap-1.5 lg:inline-flex">
                    {Object.entries(graphStats)
                      .sort((a, b) => b[1] - a[1])
                      .map(([type, count]) => (
                        <span
                          key={type}
                          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2 py-0.5 text-[11px] font-medium text-muted"
                        >
                          {type}
                          <span className="text-accent">{count}</span>
                        </span>
                      ))}
                  </span>
                )}
                {graph && graph.nodes.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => setFullGraphOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-muted transition hover:border-accent/40 hover:text-accent"
                  >
                    <Maximize2 className="h-3.5 w-3.5" />
                    Open Full Graph
                  </button>
                ) : null}
              </div>
            }
          >
            {graph && graph.nodes.length > 0 ? (
              <div className="overflow-hidden rounded-[14px] border border-border">
                <RelationshipGraphExplorer graph={graph} compact height={660} />
              </div>
            ) : (
              <EmptyState message="No relationships could be built for this investigation." />
            )}
          </Section>

          <AnimatePresence>
            {fullGraphOpen && graph && graph.nodes.length > 0 ? (
              <motion.div
                aria-modal="true"
                className="fixed inset-0 z-[100] h-dvh w-dvw overflow-hidden bg-bg"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                role="dialog"
              >
                <RelationshipGraphExplorer
                  fullscreen
                  graph={graph}
                  onExitFullscreen={() => setFullGraphOpen(false)}
                  subtitle={query}
                  title="Full Investigation Graph"
                />
              </motion.div>
            ) : null}
          </AnimatePresence>

          <AiInvestigationPanel reasoning={reasoning} processingMs={processingMs} />

          {/* Structured analyst report — every grounded section rendered professionally */}
          {reasoning.analyst_report && <AnalystReportSections report={reasoning.analyst_report} />}

          {/* KPI row */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <StatCard label="Records" value={String(pkg!.records.length)} tone="accent" icon={<FileText className="h-4 w-4" />} />
            <StatCard label="Entities" value={String(pkg!.canonical_companies.length)} icon={<Building2 className="h-4 w-4" />} />
            <StatCard label="Awards" value={String(awards.length)} tone="success" icon={<Award className="h-4 w-4" />} />
            <StatCard label="Awarded value" value={formatCompactMoney(String(awardedValue))} />
            <StatCard
              label="Indicators"
              value={String(pkg!.indicators.length)}
              tone={pkg!.indicators.some((i) => i.severity === "high") ? "danger" : "warning"}
              icon={<Gauge className="h-4 w-4" />}
            />
          </div>

          {/* Analyst trace + grounding/memory rail */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Section eyebrow="Reasoning path" title="Analyst trace">
                {reasoning.analyst_trace.length === 0 ? (
                  <EmptyState message="No analyst steps recorded." />
                ) : (
                  <AnalystTrace steps={reasoning.analyst_trace} />
                )}
              </Section>
            </div>
            <div className="space-y-5">
              <Section eyebrow="Verification" title="Grounding">
                <GroundingCard grounding={reasoning.grounding} confidence={reasoning.confidence} />
              </Section>
              {reasoning.prior_investigations.length > 0 && (
                <Section eyebrow="AI memory" title="Previous investigations">
                  <AiMemory hits={reasoning.prior_investigations} onReuse={onFollowUp} />
                </Section>
              )}
            </div>
          </div>

          {/* Flagship evidence ledger */}
          <Section
            eyebrow="Provenance"
            title="Evidence ledger"
            action={
              <span className="inline-flex items-center gap-1.5 text-xs text-faint">
                <FileText className="h-3.5 w-3.5" />
                {reasoning.evidence_ledger.length} cited items
              </span>
            }
          >
            {reasoning.evidence_ledger.length === 0 ? (
              <EmptyState message="No evidence citations were produced for this investigation." />
            ) : (
              <EvidenceLedger items={reasoning.evidence_ledger} />
            )}
          </Section>

          {/* AI findings (cited) */}
          {reasoning.findings.length > 0 && (
            <Section eyebrow="AI reasoning" title="Findings & evidence">
              <div className="space-y-3">
                {reasoning.findings.map((f, i) => (
                  <FindingCard key={i} finding={f} />
                ))}
              </div>
            </Section>
          )}

          {/* Recommendations + follow-ups */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Section eyebrow="Guidance" title="Recommendations">
              {reasoning.recommendations.length === 0 ? (
                <EmptyState message="No recommendations." />
              ) : (
                <ul className="space-y-2.5">
                  {reasoning.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-muted">
                      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section eyebrow="Next steps" title="Suggested investigations">
              {reasoning.follow_ups.length === 0 ? (
                <EmptyState message="No follow-ups." />
              ) : (
                <div className="flex flex-col gap-2">
                  {reasoning.follow_ups.map((f, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => onFollowUp(f.query)}
                      className="group flex items-center justify-between gap-3 rounded-[12px] border border-border bg-bg-2/40 p-3 text-left transition hover:border-accent/40"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-text group-hover:text-accent">{f.label}</span>
                        <span className="block truncate text-xs text-faint">{f.rationale}</span>
                      </span>
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted transition group-hover:translate-x-0.5 group-hover:text-accent" />
                    </button>
                  ))}
                </div>
              )}
            </Section>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            {/* timeline */}
            <Section eyebrow="Chronology" title="Procurement timeline">
              {timelineItems.length === 0 ? <EmptyState message="No dated events." /> : <Timeline items={timelineItems} />}
            </Section>

            {/* canonical companies */}
            <div className="lg:col-span-2">
              <Section eyebrow="Entities" title="Resolved companies">
                {pkg!.canonical_companies.length === 0 ? (
                  <EmptyState message="No entities resolved." />
                ) : (
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {pkg!.canonical_companies.map((c) => (
                      <div key={c.id} className="rounded-[12px] border border-border bg-bg-2/40 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium text-text">{c.canonical_name}</span>
                          <span className="shrink-0 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] font-semibold text-accent">
                            {Math.round((c.confidence ?? 0) * 100)}%
                          </span>
                        </div>
                        {c.aliases.length > 0 && (
                          <div className="mt-1 truncate text-xs text-faint">aka {c.aliases.slice(0, 3).join(", ")}</div>
                        )}
                        <div className="mt-1.5 text-[11px] text-muted">{c.matched_sources.length} matched sources</div>
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            </div>
          </div>

          {/* records / awards — Indian sources first */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Section eyebrow="Procurement" title={`Tender records (${pkg!.records.length})`}>
              <ul className="divide-y divide-border">
                {orderedRecords.slice(0, 12).map((r, i) => (
                  <li key={i} className="py-2.5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-text">{r.tender.title}</span>
                        <span className="block truncate font-mono text-[11px] text-faint">{r.tender.reference_number}</span>
                      </span>
                      <span className="shrink-0 tabular text-sm text-muted">
                        {formatMoneyFull(r.tender.estimated_value, r.tender.currency)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>

            <Section eyebrow="Contracts" title={`Awards (${awards.length})`}>
              {awards.length === 0 ? (
                <EmptyState message="No awards in this investigation." />
              ) : (
                <ul className="divide-y divide-border">
                  {awards.slice(0, 12).map((a, i) => (
                    <li key={i} className="flex items-center justify-between gap-3 py-2.5">
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-text">{a.company_name}</span>
                        <span className="block truncate text-xs text-faint">
                          {formatDate(a.award_date)} · {a.tender_reference_number}
                        </span>
                      </span>
                      <span className="shrink-0 tabular text-sm font-semibold text-text">
                        {formatMoneyFull(a.award_value, a.currency)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </div>

          {/* web evidence */}
          <Section
            eyebrow="Open source"
            title="Web procurement evidence"
            action={
              <button
                type="button"
                onClick={onWebSearch}
                disabled={webBusy}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted transition hover:text-text disabled:opacity-60"
              >
                {webBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Globe2 className="h-3.5 w-3.5" />}
                {webBusy ? "Searching web…" : "Search web"}
              </button>
            }
          >
            {webBusy && webPages.length === 0 ? (
              <div className="space-y-2">
                <SkeletonBlock className="h-14" />
                <SkeletonBlock className="h-14" />
              </div>
            ) : webPages.length === 0 ? (
              <EmptyState
                icon={<Globe2 className="h-5 w-5" />}
                title="No stored web evidence"
                message="Run a web search to collect open-source procurement evidence for this entity."
              />
            ) : (
              <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                {webPages.map((p, i) => {
                  const pe = p.procurement_evidence;
                  const ev: EvidenceItem = {
                    title: p.title ?? pe?.contract_title ?? p.url,
                    source: p.source,
                    sourceUrl: p.url,
                    date: pe?.publication_date ?? pe?.award_date ?? p.retrieved_at,
                    reference: pe?.contract_number ?? pe?.tender_number ?? null,
                    detail: pe?.contract_value
                      ? `Contract: ${pe.contract_value} ${pe.currency ?? ""}`.trim()
                      : pe?.government_buyer ?? null,
                    kind: "web",
                    evidenceType: pe ? "Procurement web evidence" : "Open-source page",
                    citation: `${p.title ?? pe?.contract_title ?? "Web procurement evidence"}. ${p.source}. Retrieved ${formatDate(p.retrieved_at)}.`,
                    relatedEntities: [
                      pe?.company_name,
                      ...(pe?.related_companies ?? []),
                      ...p.extraction.company_mentions
                    ].filter((value): value is string => Boolean(value)).slice(0, 6),
                    relatedContracts: [
                      pe?.contract_number,
                      pe?.contract_title
                    ].filter((value): value is string => Boolean(value)),
                    relatedTenders: [
                      pe?.tender_number,
                      pe?.tender_title,
                      pe?.tender_id
                    ].filter((value): value is string => Boolean(value)),
                    relatedOrganizations: [
                      pe?.organization,
                      pe?.government_buyer,
                      ...p.extraction.organization_names,
                      ...p.extraction.government_entities
                    ].filter((value): value is string => Boolean(value)).slice(0, 6),
                    tags: [
                      pe?.tender_category,
                      pe?.procurement_sector,
                      pe?.country,
                      p.source,
                      ...p.extraction.dates.slice(0, 2)
                    ].filter((value): value is string => Boolean(value)).slice(0, 6)
                  };
                  return <EvidenceCard key={p.id} item={ev} index={i} />;
                })}
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}

/* ============================================================ entity candidates */

function EntityCandidatesPanel({
  resolution,
  onSelect
}: {
  resolution: EntityResolutionResult;
  onSelect: (query: string) => void;
}) {
  const { candidates, requires_disambiguation, resolved } = resolution;
  const title = requires_disambiguation
    ? "Multiple entities match — select one"
    : "Resolved canonical entity";
  const eyebrow = requires_disambiguation ? "Disambiguation" : "Entity resolution";

  return (
    <Section
      eyebrow={eyebrow}
      title={title}
      action={
        <span className="text-xs text-faint">
          {candidates.length} candidate{candidates.length === 1 ? "" : "s"}
          {resolved ? " · confident match" : ""}
        </span>
      }
    >
      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
        {candidates.map((c) => {
          const isBuyer = c.entity_type === "government_buyer";
          const Icon = isBuyer ? Building2 : Award;
          return (
            <button
              key={c.entity_id}
              type="button"
              onClick={() => onSelect(c.canonical_name)}
              className="group flex flex-col gap-2 rounded-[14px] border border-border bg-bg-2/40 p-3.5 text-left transition hover:border-accent/40 hover:bg-bg-2/70"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-accent" />
                  <span className="text-sm font-semibold text-fg">{c.canonical_name}</span>
                </div>
                <span className="rounded-md border border-border bg-surface px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                  {isBuyer ? "Buyer" : "Company"}
                </span>
              </div>
              <p className="text-xs text-faint">{c.match_reason}</p>
              <div className="mt-auto flex items-center gap-2 text-[11px] text-muted">
                <span className="rounded bg-surface px-1.5 py-0.5">{c.match_type}</span>
                <span>score {c.score}</span>
                {c.tender_count > 0 && <span>· {c.tender_count} tenders</span>}
                {c.award_count > 0 && <span>· {c.award_count} awards</span>}
                <ChevronRight className="ml-auto h-3.5 w-3.5 opacity-0 transition group-hover:opacity-100" />
              </div>
            </button>
          );
        })}
      </div>
    </Section>
  );
}

/* ============================================================ finding card */

function FindingCard({ finding }: { finding: ReasoningFinding }) {
  const [open, setOpen] = useState(false);
  const citations = finding.citations;
  return (
    <div className="rounded-[14px] border border-border bg-bg-2/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-text">{finding.title}</h4>
          <p className="mt-1 text-sm text-muted">{finding.detail}</p>
        </div>
        <SeverityBadge severity={finding.severity} score={finding.score} />
      </div>

      {citations.length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center gap-1.5 text-[11px] font-medium text-accent transition hover:text-accent-hi"
          >
            <ChevronRight className={`h-3.5 w-3.5 transition ${open ? "rotate-90" : ""}`} />
            {citations.length} source citation{citations.length > 1 ? "s" : ""}
          </button>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <ul className="mt-2 space-y-1.5">
                  {citations.map((c, i) => (
                    <li key={i} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface/60 px-3 py-2">
                      <span className="min-w-0">
                        <span className="block truncate text-xs text-text">{c.label}</span>
                        <span className="block truncate text-[11px] text-faint">
                          {c.source_name}
                          {c.related_tender ? ` · ${c.related_tender}` : ""}
                        </span>
                      </span>
                      {c.source_url ? (
                        <a
                          href={c.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex shrink-0 items-center gap-1 text-[11px] text-accent hover:underline"
                        >
                          Verify <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="shrink-0 text-[11px] text-faint">{c.source_record_id ?? "—"}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
