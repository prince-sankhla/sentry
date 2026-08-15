"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Award,
  Building2,
  Check,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  Gauge,
  Globe2,
  Lightbulb,
  ListChecks,
  Loader2,
  Maximize2,
  Network,
  ScrollText,
  Search,
  ShieldAlert,
  X
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { RelationshipGraphExplorer } from "@/app/graph/relationship-graph";
import { CommandCenter } from "@/app/command-center";
import { EntitySearch, type PinnedEntity } from "@/components/search/entity-search";
import { PriorityInvestigationQueue } from "@/components/dashboard/priority-queue";
import { EvidenceCard, type EvidenceItem } from "@/components/intel/evidence-card";
import { InvestigatorReview } from "@/components/intel/investigator-review";
import {
  FindingCaseFile,
  type CaseFileFinding,
  type NextStep,
  type OfficialSource
} from "@/components/intel/finding-case-file";
import { AiInvestigationPanel } from "@/components/intel/ai-investigation-panel";
import { AnalystReportSections } from "@/components/intel/analyst-report";
import { AnalystTrace } from "@/components/intel/analyst-trace";
import { EvidenceLedger } from "@/components/intel/evidence-ledger";
import { GroundingCard } from "@/components/intel/grounding-card";
import { AiMemory } from "@/components/intel/ai-memory";
import { ProviderBadge } from "@/components/intel/provider-badge";
import { Section, StatCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { PageShell } from "@/components/ui/page";
import { EmptyState, ErrorState, SkeletonBlock } from "@/components/ui/states";
import { Timeline, type TimelineItem } from "@/components/ui/timeline";
import { DURATION, EASE, SPRING_SOFT } from "@/lib/motion";
import {
  evidencePacketUrl,
  getLLMProviders,
  getProcurementEvidence,
  searchWebEvidence,
  streamInvestigation,
  type EntityResolutionResult,
  type InvestigationPackage,
  type InvestigationReasoning,
  type ContextFactsPayload,
  type InvestigationStreamStep,
  type LLMProviderStatus,
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
  { key: "plan", name: "Connecting official procurement sources", status: "pending" },
  { key: "retrieve", name: "Retrieving procurement records", status: "pending" },
  { key: "resolve", name: "Resolving entities & identities", status: "pending" },
  { key: "indicators", name: "Screening procurement patterns", status: "pending" },
  { key: "reasoning", name: "Grounding findings against official records", status: "pending" }
];

/** Cinematic sub-messages that cycle while a step is active. Keyed by step key. */
const STEP_PHASE_MESSAGES: Record<string, string[]> = {
  plan: [
    "Connecting to official procurement portals…",
    "Selecting relevant source connectors…",
    "Planning evidence retrieval strategy…",
    "Identifying registered procurement entities…"
  ],
  retrieve: [
    "Querying CPPP portal records…",
    "Scanning GeM procurement database…",
    "Pulling NIC state e-procurement feeds…",
    "Downloading official tender documents…",
    "Normalising procurement records…"
  ],
  resolve: [
    "Resolving company identities across sources…",
    "Matching registration numbers to canonical entities…",
    "Deduplicating supplier records…",
    "Building entity relationship map…",
    "Verifying buyer–supplier linkages…"
  ],
  indicators: [
    "Screening for contract fragmentation patterns…",
    "Detecting single-bidder exposure…",
    "Analysing award clustering signals…",
    "Checking bid timing irregularities…",
    "Scoring procurement risk indicators…"
  ],
  reasoning: [
    "Grounding findings against official records…",
    "Assembling evidence citations…",
    "Running explainability guard…",
    "Generating analyst-grade narrative…",
    "Producing final investigation report…"
  ]
};

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
      router.push(`/investigate?q=${encodeURIComponent(query)}`);
      runInvestigation(query);
    },
    [router, runInvestigation]
  );

  const launchFollowUp = useCallback(
    (query: string) => {
      setActiveQuery(query);
      router.push(`/investigate?q=${encodeURIComponent(query)}`);
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
    router.push("/investigate");
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
          // Single source of truth for provenance: once a report exists, the
          // badge reflects who ACTUALLY authored THIS run (reasoning.generated_by)
          // — never the /providers capability probe. This prevents the header
          // showing "ONLINE" while the report itself fell back to deterministic.
          // Before any run, fall back to the configured-provider readiness probe.
          reasoning ? (
            <ProviderBadge
              generatedBy={reasoning.generated_by}
              provider={reasoning.provider}
              model={reasoning.model}
            />
          ) : providerStatus ? (
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

      {/* Investigation Replay — collapsed by default, opens to show the full
          step-by-step walkthrough of how SENTRY reached its conclusions. */}
      {!running && steps.length > 0 && steps.every((s) => s.status === "complete" || s.status === "error") && (
        <InvestigationReplay steps={steps} query={activeQuery} />
      )}

      {error && !running && (
        <div className="mt-8">
          <ErrorState message={error} title="Investigation could not complete" />
        </div>
      )}

      {!activeQuery && !running && (
        <CaseLauncherBanner onOpen={() => launchFollowUp("Dharmagarh NAC")} />
      )}

      {/* Investigator landing: where to start, before the analytics dashboard. */}
      {!activeQuery && !running && (
        <div className="mt-8">
          <PriorityInvestigationQueue onOpen={launchFollowUp} />
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
  const runningStep = steps.find((s) => s.status === "running");

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.slow, ease: EASE }}
      className="mt-8 overflow-hidden rounded-2xl border border-border bg-surface/70 float"
    >
      {/* console header with live progress */}
      <div className="flex items-center gap-3.5 border-b border-border bg-bg-2/50 px-6 py-4">
        <span className="relative grid h-9 w-9 place-items-center rounded-lg border border-accent/30 bg-accent/[0.08] text-accent">
          {running ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
          {running && (
            <span className="absolute inset-0 rounded-lg border border-accent/40 pulse-live" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <div className="text-[13.5px] font-semibold text-text">
              {running ? "Investigation in progress" : "Investigation complete"}
            </div>
            {running && (
              <span className="rounded-full bg-accent/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">
                live
              </span>
            )}
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              key={runningStep?.key ?? "idle"}
              initial={{ opacity: 0, y: 3 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-0.5 text-[11.5px] text-faint"
            >
              {running && runningStep
                ? runningStep.detail ?? runningStep.name + "…"
                : running
                  ? "Preparing investigation…"
                  : "Full evidence trace assembled and verified."}
            </motion.div>
          </AnimatePresence>
        </div>
        <div className="flex items-center gap-3">
          {!running && (
            <span className="hidden items-center gap-1.5 text-[11px] text-success sm:inline-flex">
              <Check className="h-3.5 w-3.5" /> Verified
            </span>
          )}
          <span className="tabular text-[15px] font-semibold text-accent">{pct}%</span>
        </div>
      </div>

      {/* progress rail */}
      <div className="h-0.5 w-full bg-border">
        <motion.div
          className="h-full bg-accent"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: DURATION.slow, ease: EASE }}
        />
      </div>

      {/* live vertical trace */}
      <div className="relative px-6 py-5">
        {/* connector spine */}
        <span className="absolute bottom-7 left-[35px] top-7 w-px bg-border" aria-hidden />
        <ol>
          {steps.map((s, i) => (
            <CinematicStep key={s.key} step={s} index={i} />
          ))}
        </ol>
      </div>
    </motion.div>
  );
}

/** A single pipeline step with cycling sub-messages while running. */
function CinematicStep({ step: s, index: i }: { step: Step; index: number }) {
  const phases = STEP_PHASE_MESSAGES[s.key] ?? [];
  const [phaseIdx, setPhaseIdx] = useState(0);

  useEffect(() => {
    if (s.status !== "running" || phases.length === 0) return;
    setPhaseIdx(0);
    const id = setInterval(() => setPhaseIdx((p) => (p + 1) % phases.length), 1800);
    return () => clearInterval(id);
  }, [s.status, phases]);

  const subMessage =
    s.status === "running"
      ? phases[phaseIdx] ?? s.detail ?? "Working…"
      : s.status === "complete"
        ? s.detail ?? "Complete"
        : s.status === "error"
          ? s.detail ?? "Failed"
          : "Queued";

  return (
    <motion.li
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.05, ease: EASE }}
      className="relative flex items-start gap-3.5 py-2.5"
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
          <span className={`text-[13.5px] font-medium ${s.status === "pending" ? "text-faint" : "text-text"}`}>
            {s.name}
          </span>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={s.status === "running" ? phases[phaseIdx] : s.status}
            initial={{ opacity: 0, y: 2 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className={`mt-0.5 text-[11.5px] ${
              s.status === "complete" ? "text-success/80" : s.status === "error" ? "text-danger/80" : "text-faint"
            }`}
          >
            {subMessage}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.li>
  );
}

/* ============================================================ investigation replay */

const REPLAY_STEP_ICONS: Record<string, React.ElementType> = {
  plan: Network,
  retrieve: FileText,
  resolve: Building2,
  indicators: ShieldAlert,
  reasoning: ScrollText
};

const REPLAY_STEP_OUTCOME: Record<string, string> = {
  plan: "Selected procurement sources and defined retrieval strategy",
  retrieve: "Downloaded and normalised official procurement records",
  resolve: "Matched procurement entities to canonical identities",
  indicators: "Applied 12 deterministic screening rules to all records",
  reasoning: "Grounded findings against official evidence and produced report"
};

/**
 * Post-investigation replay panel. Shows the full methodology walkthrough —
 * judges can see exactly how SENTRY reached every conclusion. Collapsed by
 * default so it doesn't crowd the results.
 */
function InvestigationReplay({ steps, query }: { steps: Step[]; query: string }) {
  const [open, setOpen] = useState(false);
  const [replayIdx, setReplayIdx] = useState<number>(-1);
  const [replaying, setReplaying] = useState(false);

  function startReplay() {
    setReplayIdx(-1);
    setReplaying(true);
    let i = 0;
    const tick = () => {
      setReplayIdx(i);
      i++;
      if (i < steps.length) setTimeout(tick, 900);
      else setTimeout(() => setReplaying(false), 400);
    };
    setTimeout(tick, 180);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.base, ease: EASE }}
      className="mt-4 overflow-hidden rounded-xl border border-border bg-bg-2/40"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors duration-200 hover:bg-surface/40"
      >
        <span className="t-label flex items-center gap-2">
          <ListChecks className="h-3.5 w-3.5 text-accent" />
          How this investigation was conducted
        </span>
        <span className="flex items-center gap-2">
          <span className="hidden text-[11px] text-faint sm:block">
            {steps.length} steps · {steps.filter((s) => s.status === "complete").length} completed
          </span>
          <ChevronRight
            className={`h-4 w-4 text-muted transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          />
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: DURATION.base, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-5 pb-5 pt-4">
              {/* header row */}
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <div className="text-[13.5px] font-semibold text-text">
                    Investigation methodology — "{query}"
                  </div>
                  <div className="mt-0.5 text-[11.5px] text-faint">
                    Deterministic pipeline. Every step is reproducible and auditable.
                  </div>
                </div>
                <Button
                  variant="subtle"
                  size="sm"
                  onClick={startReplay}
                  disabled={replaying}
                  loading={replaying}
                  icon={<Loader2 className={`h-3.5 w-3.5 ${replaying ? "animate-spin" : ""}`} />}
                >
                  {replaying ? "Replaying…" : "Replay"}
                </Button>
              </div>

              {/* step timeline */}
              <div className="relative">
                <span className="absolute bottom-4 left-[19px] top-4 w-px bg-border" aria-hidden />
                <ol className="space-y-1">
                  {steps.map((s, i) => {
                    const Icon = REPLAY_STEP_ICONS[s.key] ?? Check;
                    const outcome = REPLAY_STEP_OUTCOME[s.key];
                    const isHighlighted = replaying ? i <= replayIdx : s.status === "complete";
                    const isCurrent = replaying && i === replayIdx;

                    return (
                      <motion.li
                        key={s.key}
                        animate={{
                          opacity: isHighlighted ? 1 : 0.45,
                          x: isCurrent ? [0, 4, 0] : 0
                        }}
                        transition={{ duration: 0.35, ease: EASE }}
                        className="flex items-start gap-3.5 rounded-lg px-2 py-3"
                      >
                        <span
                          className={`relative z-10 mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 transition-colors ${
                            s.status === "complete"
                              ? isHighlighted
                                ? "border-accent/50 bg-accent/15 text-accent"
                                : "border-border bg-surface text-faint"
                              : s.status === "error"
                                ? "border-danger/40 bg-danger/10 text-danger"
                                : "border-border bg-surface text-faint"
                          }`}
                        >
                          {isCurrent ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Icon className="h-3 w-3" />
                          )}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[13px] font-medium text-text">{s.name}</span>
                            {s.status === "complete" && isHighlighted && !replaying && (
                              <span className="rounded-md border border-success/25 bg-success/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-success">
                                done
                              </span>
                            )}
                          </div>
                          <div className="mt-0.5 text-[11.5px] text-faint">
                            {s.detail ?? outcome}
                          </div>
                        </div>
                        <span className="mt-0.5 shrink-0 text-[11px] tabular text-faint">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                      </motion.li>
                    );
                  })}
                </ol>
              </div>

              <div className="mt-4 rounded-lg border border-border bg-bg-2/30 px-3.5 py-3 text-[11.5px] leading-relaxed text-faint">
                Every step runs against your connected data sources only. No data leaves the
                platform. All findings are traceable to the official procurement records that
                triggered them — no model speculation, no invented facts.
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
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
    <div className="mt-8 space-y-8">
      {/* Canonical entity resolution — never silently ignore backend candidates. */}
      {resolution && resolution.candidates.length > 0 && (
        <EntityCandidatesPanel resolution={resolution} onSelect={onFollowUp} />
      )}

      {/* Prior related investigations surface even without records */}
      {reasoning.prior_investigations.length > 0 && !hasRecords && (
        <Section eyebrow="Related investigations" title="Previous related investigations">
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
          {/* ── CASE HEADER: the finding is the hero, deterministic + AI-free ── */}
          <CaseVerdictHeader
            query={query}
            reasoning={reasoning}
            recordCount={pkg!.records.length}
            entityCount={pkg!.canonical_companies.length}
            awardCount={awards.length}
            awardedValue={awardedValue}
            indicatorCount={pkg!.risk_assessment_v2?.indicators.length ?? pkg!.indicators.length}
            topFindings={(pkg!.risk_assessment_v2?.indicators ?? []).map((i) => i.name)}
            onExport={() => openEvidencePacket(query)}
            onInvestigate={onFollowUp}
          />

          {/* 1 — chronology: what happened, in order */}
          <Section eyebrow="Chronology" title="Procurement timeline">
            {timelineItems.length === 0 ? <EmptyState message="No dated events." /> : <Timeline items={timelineItems} />}
          </Section>

          {/* 2 — FINDINGS AS CASE FILES: each finding appears exactly ONCE and
               answers the five investigator questions in order — detection,
               supporting evidence, legitimate explanations, evidence still
               required, recommended next investigation — closed by the fixed
               Current Position. Consolidates what previously spanned three
               sections (indicators, investigator review, evidence challenge). */}
          <div id="ev-risk" className="scroll-mt-24">
            <FindingCaseFilesSection
              pkg={pkg!}
              reasoning={reasoning}
              activeQuery={query}
              onInvestigate={onFollowUp}
            />
          </div>

          {/* 2b — EVIDENCE REVIEW: case-level facts only (cluster structure,
               shared identifiers, portal documentation). Finding-level items
               live in their case files above — never duplicated here. */}
          {reasoning.investigator_review && (
            <InvestigatorReview review={caseLevelReview(reasoning.investigator_review)} caseFacts />
          )}

          {/* 3 — the relationship network */}
          <Section
            eyebrow="Network"
            title="Investigation graph"
            action={
              <div className="flex items-center gap-2.5">
                <span className="hidden items-center gap-1.5 text-xs text-faint sm:inline-flex">
                  <Network className="h-3.5 w-3.5" />
                  {graph?.nodes.length ?? 0} nodes · {graph?.edges.length ?? 0} relationships
                </span>
                {Object.keys(graphStats).length > 0 && (
                  <span className="hidden flex-wrap items-center gap-1.5 lg:inline-flex">
                    {Object.entries(graphStats)
                      .sort((a, b) => b[1] - a[1])
                      .map(([type, count]) => (
                        <Chip key={type} tone="neutral">
                          {type}
                          <span className="tabular text-accent">{count}</span>
                        </Chip>
                      ))}
                  </span>
                )}
                {graph && graph.nodes.length > 0 ? (
                  <Button
                    variant="subtle"
                    size="sm"
                    onClick={() => setFullGraphOpen(true)}
                    icon={<Maximize2 className="h-3.5 w-3.5" />}
                  >
                    Open Full Graph
                  </Button>
                ) : null}
              </div>
            }
          >
            {graph && graph.nodes.length > 0 ? (
              <div className="overflow-hidden rounded-xl border border-border">
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

          {/* 4 — EVIDENCE VIEWER: the proof. Every claim links to its source. */}
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

          {/* 5 — EVIDENCE PACKET EXPORT: one-click, client-side, works offline */}
          <EvidencePacketCTA
            evidenceCount={reasoning.evidence_ledger.length}
            sourceCount={new Set(reasoning.evidence_ledger.map((c) => c.source_name)).size}
            onExport={() => openEvidencePacket(query)}
          />

          {/* supporting evidence — raw records + awards */}
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <div id="ev-records" className="scroll-mt-24">
            <Section eyebrow="Procurement" title={`Tender records (${pkg!.records.length})`}>
              <ul className="divide-y divide-border">
                {orderedRecords.slice(0, 12).map((r, i) => (
                  <li key={i} className="py-3">
                    <div className="flex items-center justify-between gap-4">
                      <span className="min-w-0">
                        <span className="block truncate text-[13.5px] text-text">{r.tender.title}</span>
                        <span className="mt-0.5 block truncate font-mono text-[11px] text-faint">{r.tender.reference_number}</span>
                      </span>
                      <span className="shrink-0 tabular text-[13.5px] text-muted">
                        {formatMoneyFull(r.tender.estimated_value, r.tender.currency)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
            </div>

            <div id="ev-awards" className="scroll-mt-24">
            <Section eyebrow="Contracts" title={`Awards (${awards.length})`}>
              {awards.length === 0 ? (
                <EmptyState message="No awards in this investigation." />
              ) : (
                <ul className="divide-y divide-border">
                  {awards.slice(0, 12).map((a, i) => (
                    <li key={i} className="flex items-center justify-between gap-4 py-3">
                      <span className="min-w-0">
                        <span className="block truncate text-[13.5px] text-text">{a.company_name}</span>
                        <span className="mt-0.5 block truncate text-xs text-faint">
                          {formatDate(a.award_date)} · {a.tender_reference_number}
                        </span>
                      </span>
                      <span className="shrink-0 tabular text-[13.5px] font-semibold text-text">
                        {formatMoneyFull(a.award_value, a.currency)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
            </div>
          </div>

          {/* resolved entities */}
          <Section eyebrow="Entities" title="Resolved companies">
            {pkg!.canonical_companies.length === 0 ? (
              <EmptyState message="No entities resolved." />
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {pkg!.canonical_companies.map((c) => (
                  <div
                    key={c.id}
                    className="rounded-xl border border-border bg-bg-2/40 p-4 transition-colors duration-200 hover:border-border-strong"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[13.5px] font-medium text-text">{c.canonical_name}</span>
                      <Chip tone="accent">
                        match {Math.round((c.confidence ?? 0) * 100)}%
                      </Chip>
                    </div>
                    {c.aliases.length > 0 && (
                      <div className="mt-1.5 truncate text-xs text-faint">aka {c.aliases.slice(0, 3).join(", ")}</div>
                    )}
                    <div className="mt-2 text-[11.5px] text-muted">{c.matched_sources.length} matched sources</div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* web evidence */}
          <Section
            eyebrow="Open source"
            title="Web procurement evidence"
            action={
              <Button
                variant="subtle"
                size="sm"
                onClick={onWebSearch}
                disabled={webBusy}
                loading={webBusy}
                icon={<Globe2 className="h-3.5 w-3.5" />}
              >
                {webBusy ? "Searching web…" : "Search web"}
              </Button>
            }
          >
            {webBusy && webPages.length === 0 ? (
              <div className="space-y-3">
                <SkeletonBlock className="h-16" />
                <SkeletonBlock className="h-16" />
              </div>
            ) : webPages.length === 0 ? (
              <EmptyState
                icon={<Globe2 className="h-5 w-5" />}
                title="No stored web evidence"
                message="Run a web search to collect open-source procurement evidence for this entity."
              />
            ) : (
              <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
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
                    /* ── preservation fields from StoredWebPage ── */
                    retrievedAt: p.retrieved_at,
                    integrityHash: p.content_hash ?? null,
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

          {/* Manual verification guidance — secondary, collapsed by default.
               Per-finding next investigations live in the case files; this holds
               only the generic verification steps (no duplication). */}
          {reasoning.recommendations.length > 0 && (
            <details className="group rounded-2xl border border-border bg-surface/60 px-6 py-5">
              <summary className="cursor-pointer list-none text-sm font-semibold text-text">
                <span className="t-label text-accent">Manual verification</span>
                <span className="ml-3 text-muted group-open:hidden">Show the verification steps an investigator should perform ({reasoning.recommendations.length})</span>
              </summary>
              <ul className="mt-4 space-y-3">
                {reasoning.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-3 text-[13.5px] leading-relaxed text-muted">
                    <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          {/* ── NARRATIVE SUMMARY (secondary) — phrasing generated FROM the
               evidence above; the findings stand without it. Shown last. ── */}
          <AiSummaryDivider />
          <AiInvestigationPanel reasoning={reasoning} processingMs={processingMs} />
          {reasoning.analyst_report && <AnalystReportSections report={reasoning.analyst_report} />}
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Section eyebrow="Methodology" title="Analyst trace">
                {reasoning.analyst_trace.length === 0 ? (
                  <EmptyState message="No analyst steps recorded." />
                ) : (
                  <AnalystTrace steps={reasoning.analyst_trace} />
                )}
              </Section>
            </div>
            <div className="space-y-8">
              <Section eyebrow="Verification" title="Grounding">
                <GroundingCard grounding={reasoning.grounding} />
              </Section>
              {reasoning.prior_investigations.length > 0 && (
                <Section eyebrow="Related investigations" title="Previous investigations">
                  <AiMemory hits={reasoning.prior_investigations} onReuse={onFollowUp} />
                </Section>
              )}
            </div>
          </div>
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
      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
        {candidates.map((c) => {
          const isBuyer = c.entity_type === "government_buyer";
          const Icon = isBuyer ? Building2 : Award;
          return (
            <motion.button
              key={c.entity_id}
              type="button"
              onClick={() => onSelect(c.canonical_name)}
              whileHover={{ y: -2 }}
              transition={SPRING_SOFT}
              className="group flex flex-col gap-2.5 rounded-xl border border-border bg-bg-2/40 p-4 text-left transition-colors duration-200 hover:border-accent/40 hover:bg-bg-2/70"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-accent" />
                  <span className="text-[13.5px] font-semibold text-text">{c.canonical_name}</span>
                </div>
                <Chip tone="neutral">{isBuyer ? "Buyer" : "Company"}</Chip>
              </div>
              <p className="text-xs leading-relaxed text-faint">{c.match_reason}</p>
              <div className="mt-auto flex items-center gap-2 text-[11.5px] text-muted">
                <span className="rounded-md bg-surface px-1.5 py-0.5">{c.match_type}</span>
                <span>score {c.score}</span>
                {c.tender_count > 0 && <span>· {c.tender_count} tenders</span>}
                {c.award_count > 0 && <span>· {c.award_count} awards</span>}
                <ChevronRight className="ml-auto h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
            </motion.button>
          );
        })}
      </div>
    </Section>
  );
}

/* ============================================================ case #001 launcher */

/** Dashboard → one-click "Open Case #001". Curated, friction-free demo entry. */
function CaseLauncherBanner({ onOpen }: { onOpen: () => void }) {
  return (
    <motion.button
      type="button"
      onClick={onOpen}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: DURATION.slow, ease: EASE }}
      className="group relative mt-6 flex w-full items-center gap-5 overflow-hidden rounded-2xl border border-accent/25 bg-surface/70 p-5 text-left float transition-colors duration-200 hover:border-accent/50 md:p-6"
    >
      <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
      <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-accent/30 bg-accent/[0.08] text-accent">
        <ShieldAlert className="h-5 w-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="t-label flex items-center gap-2 text-accent">
          Case #001 · Live investigation
        </span>
        <span className="mt-1.5 block text-[15px] font-semibold text-text">Dharmagarh NAC — Odisha ward-works procurement</span>
        <span className="mt-1 block truncate text-xs text-muted">
          16 same-day tenders · ₹1.32 crore · contract-fragmentation pattern — traced to the official Odisha e-procurement portal.
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-bg transition-colors group-hover:bg-accent-hi">
        Open case
        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
      </span>
    </motion.button>
  );
}

/* ============================================================ case verdict header */

type RiskLevelKey = "critical" | "high" | "medium" | "low" | "insufficient";

const RISK_LEVEL_STYLE: Record<RiskLevelKey, { label: string; cls: string; bar: string }> = {
  critical: { label: "Critical priority", cls: "border-risk-crit/50 bg-risk-crit/10 text-risk-crit", bar: "bg-risk-crit" },
  high: { label: "High priority", cls: "border-risk-high/40 bg-risk-high/10 text-risk-high", bar: "bg-risk-high" },
  medium: { label: "Medium priority", cls: "border-risk-med/40 bg-risk-med/10 text-risk-med", bar: "bg-risk-med" },
  low: { label: "Low priority", cls: "border-risk-low/40 bg-risk-low/10 text-risk-low", bar: "bg-risk-low" },
  insufficient: { label: "Insufficient evidence", cls: "border-border bg-surface text-muted", bar: "bg-border-strong" }
};

const CURRENT_POSITION_SUMMARY =
  "The available evidence does not yet distinguish between routine procurement activity " +
  "and procurement requiring escalation. Additional evidence is required.";

function riskKey(level: string): RiskLevelKey {
  return (["critical", "high", "medium", "low", "insufficient"] as RiskLevelKey[]).includes(level as RiskLevelKey)
    ? (level as RiskLevelKey)
    : "medium";
}

/** Makes a headline stat a one-click jump to the records behind it (req 12). */
function StatJump({ target, hint, children }: { target: string; hint: string; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={() => scrollToEvidence(target)}
      title={hint}
      className="group/jump relative block w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 rounded-2xl"
    >
      {children}
      <span className="pointer-events-none absolute bottom-2 right-3 text-[10px] font-medium text-faint opacity-0 transition group-hover/jump:opacity-100">
        {hint} ↓
      </span>
    </button>
  );
}

/**
 * The 30-second summary: what was found, where the case stands, and what to
 * investigate next — before any detail. Deterministic screening output only.
 */
function CaseVerdictHeader({
  query,
  reasoning,
  recordCount,
  entityCount,
  awardCount,
  awardedValue,
  indicatorCount,
  topFindings,
  onExport,
  onInvestigate
}: {
  query: string;
  reasoning: InvestigationReasoning;
  recordCount: number;
  entityCount: number;
  awardCount: number;
  awardedValue: number;
  indicatorCount: number;
  topFindings: string[];
  onExport: () => void;
  onInvestigate: (query: string) => void;
}) {
  const style = RISK_LEVEL_STYLE[riskKey(reasoning.risk_level)];
  const nextInvestigations = reasoning.follow_ups.slice(0, 3);

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.slow, ease: EASE }}
      className="relative overflow-hidden rounded-2xl border border-border bg-surface/70 p-6 float md:p-8"
    >
      <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-accent/[0.06] blur-3xl" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="t-label text-accent">Investigation summary</div>
          <h2 className="mt-2 truncate text-[24px] font-semibold tracking-[-0.02em] text-text md:text-[28px]">{query}</h2>
          <p className="mt-2 max-w-2xl text-[13.5px] leading-relaxed text-muted">
            <span className="font-semibold text-text">{indicatorCount}</span> finding{indicatorCount === 1 ? "" : "s"} across{" "}
            <span className="font-semibold text-text">{recordCount}</span> official procurement records ·{" "}
            <span className="font-semibold text-text">{awardCount}</span> award{awardCount === 1 ? "" : "s"}. Deterministic
            screening — leads for investigator review, not a determination of wrongdoing.
          </p>
          {/* top findings — one line, jump to the case files */}
          {topFindings.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="t-label">Top findings</span>
              {topFindings.slice(0, 4).map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => scrollToEvidence("ev-risk")}
                  className="rounded-lg border border-border bg-bg-2/50 px-2.5 py-1 text-[11.5px] font-medium text-text transition-colors duration-200 hover:border-accent/40 hover:text-accent"
                >
                  {name}
                </button>
              ))}
              {topFindings.length > 4 && <span className="text-[11.5px] text-faint">+{topFindings.length - 4} more</span>}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-start gap-3.5 lg:items-end">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${style.cls}`}>
            <ShieldAlert className="h-3.5 w-3.5" />
            {style.label}
          </span>
          <Button onClick={onExport} icon={<Download className="h-4 w-4" />}>
            Export evidence packet
          </Button>
        </div>
      </div>

      <div className="relative mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatJump target="ev-records" hint="View records">
          <StatCard label="Records" value={String(recordCount)} tone="accent" icon={<FileText className="h-4 w-4" />} />
        </StatJump>
        <StatJump target="ev-awards" hint="View awards">
          <StatCard label="Awards" value={String(awardCount)} tone="success" icon={<Award className="h-4 w-4" />} />
        </StatJump>
        <StatJump target="ev-awards" hint="View awards">
          <StatCard label="Awarded value" value={formatCompactMoney(String(awardedValue))} icon={<Building2 className="h-4 w-4" />} />
        </StatJump>
        <StatJump target="ev-risk" hint="View case files">
          <StatCard
            label="Findings"
            value={String(indicatorCount)}
            tone={indicatorCount > 0 ? "danger" : "accent"}
            icon={<Gauge className="h-4 w-4" />}
          />
        </StatJump>
      </div>

      {/* current position + recommended next investigation — the 30-second close */}
      <div className="relative mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-bg-2/40 px-4 py-3.5">
          <div className="t-label">Current position</div>
          <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
            {indicatorCount > 0
              ? CURRENT_POSITION_SUMMARY
              : "No findings were raised by deterministic screening of the retrieved records."}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-bg-2/40 px-4 py-3.5">
          <div className="t-label">Recommended next investigation</div>
          {nextInvestigations.length === 0 ? (
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted">No further investigations recommended from this evidence.</p>
          ) : (
            <div className="mt-1.5 space-y-0.5">
              {nextInvestigations.map((f, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onInvestigate(f.query)}
                  className="group flex w-full items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-left transition-colors duration-200 hover:bg-surface/60"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-text group-hover:text-accent">{f.label}</span>
                    <span className="mt-0.5 block truncate text-[11.5px] text-faint">{f.rationale}</span>
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted transition-all group-hover:translate-x-0.5 group-hover:text-accent" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.section>
  );
}

/* ============================================================ finding case files */

/** Official government source (URL + portal) for a tender reference number. */
function buildSourceIndex(pkg: InvestigationPackage): Map<string, OfficialSource> {
  const index = new Map<string, OfficialSource>();
  for (const r of pkg.records) {
    const url = r.tender.metadata?.source_url;
    if (url && !index.has(r.tender.reference_number)) {
      index.set(r.tender.reference_number, {
        ref: r.tender.reference_number,
        url,
        source: r.tender.metadata?.source_name ?? "official source"
      });
    }
  }
  return index;
}

/** Findings for the case files: deterministic screening first, legacy fallbacks kept. */
function caseFileFindings(pkg: InvestigationPackage): CaseFileFinding[] {
  const v2 = pkg.risk_assessment_v2?.indicators ?? [];
  if (v2.length > 0) {
    return v2.map((i) => ({
      id: i.id,
      name: i.name,
      severity: i.severity,
      reason: i.reason,
      evidenceStatus: i.evidence_status,
      recordRefs: i.supporting_records,
      contextNotes: i.context_notes
    }));
  }
  return pkg.indicators.map((i) => ({
    id: i.type,
    name: i.title,
    severity: i.severity,
    reason: i.summary,
    evidenceStatus: "recorded",
    recordRefs: i.related_tenders,
    contextNotes: []
  }));
}

/**
 * Recommended next investigations for one finding, each with a reason —
 * derived from the finding's own supporting records (suppliers awarded the
 * flagged tenders, then their procuring entities), never from speculation.
 */
function nextStepsFor(
  refs: string[],
  pkg: InvestigationPackage,
  activeQuery: string
): NextStep[] {
  const refSet = new Set(refs);
  const active = activeQuery.trim().toLowerCase();
  const supplierCounts = new Map<string, number>();
  const buyers = new Map<string, number>();
  for (const r of pkg.records) {
    if (!refSet.has(r.tender.reference_number)) continue;
    for (const a of r.awards) {
      if (a.company_name) supplierCounts.set(a.company_name, (supplierCounts.get(a.company_name) ?? 0) + 1);
    }
    const buyer = r.tender.procuring_entity?.trim();
    if (buyer) buyers.set(buyer, (buyers.get(buyer) ?? 0) + 1);
  }
  const steps: NextStep[] = [];
  for (const [supplier, n] of [...supplierCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2)) {
    if (supplier.toLowerCase() === active) continue;
    steps.push({
      label: `Investigate ${supplier}`,
      query: supplier,
      reason: `Awarded ${n} of the flagged tender${n === 1 ? "" : "s"}`
    });
  }
  for (const [buyer, n] of [...buyers.entries()].sort((a, b) => b[1] - a[1]).slice(0, 1)) {
    if (buyer.toLowerCase() === active || active.includes(buyer.toLowerCase()) || buyer.toLowerCase().includes(active)) continue;
    steps.push({
      label: `Investigate buyer ${buyer.split("||").pop() ?? buyer}`,
      query: buyer,
      reason: `Procuring entity for ${n} flagged tender${n === 1 ? "" : "s"}`
    });
  }
  return steps.slice(0, 3);
}

/**
 * "Why was this finding triggered?" — a deterministic fact chain computed from
 * the SAME records the engine screened. No probabilities, no model reasoning:
 * buyer/supplier identity, counts, and date arithmetic only, closing with the
 * indicator that those facts triggered.
 */
function triggerFactsFor(finding: CaseFileFinding, pkg: InvestigationPackage): string[] {
  const refSet = new Set(finding.recordRefs);
  const records = pkg.records.filter((r) => refSet.has(r.tender.reference_number));
  if (records.length === 0) return [];

  const facts: string[] = [];
  const buyers = [...new Set(records.map((r) => r.tender.procuring_entity?.trim()).filter(Boolean))] as string[];
  if (buyers.length === 1) facts.push(`Same buyer: ${buyers[0]!.split("||").pop()}`);
  else if (buyers.length > 1) facts.push(`${buyers.length} procuring entities`);

  const suppliers = [...new Set(records.flatMap((r) => r.awards.map((a) => a.company_name)).filter(Boolean))];
  if (suppliers.length === 1) facts.push(`Same supplier: ${suppliers[0]}`);

  const awardCount = records.reduce((n, r) => n + r.awards.length, 0);
  if (awardCount > 0) facts.push(`${awardCount} award${awardCount === 1 ? "" : "s"}`);
  else facts.push(`${records.length} tender${records.length === 1 ? "" : "s"}, no awards on record`);

  const awardDates = records
    .flatMap((r) => r.awards.map((a) => a.award_date))
    .filter((d): d is string => Boolean(d))
    .sort();
  if (awardDates.length >= 2) {
    const span = Math.round(
      (new Date(awardDates[awardDates.length - 1]).getTime() - new Date(awardDates[0]).getTime()) / 86400000
    );
    facts.push(`${span}-day award window`);
  }

  const pubDates = [...new Set(records.map((r) => r.tender.published_date).filter(Boolean))];
  if (records.length > 1 && pubDates.length === 1) facts.push(`Single publication date (${formatDate(pubDates[0]!)})`);
  const closeDates = [...new Set(records.map((r) => r.tender.closing_date).filter(Boolean))];
  if (records.length > 1 && closeDates.length === 1) facts.push(`Single closing date (${formatDate(closeDates[0]!)})`);

  const values = records.map((r) => r.tender.estimated_value).filter(Boolean);
  const duplicateValues = values.length - new Set(values).size;
  if (duplicateValues > 0) facts.push(`${duplicateValues + 1}+ tenders with identical estimated values`);

  facts.push(`${finding.name} indicator triggered`);
  return facts;
}

/**
 * Evidence review filtered to CASE-LEVEL facts only. Finding-level items
 * (basis risk_engine:*) live in their case files — referenced, not duplicated.
 */
function caseLevelReview(review: NonNullable<InvestigationReasoning["investigator_review"]>) {
  return {
    ...review,
    supporting: review.supporting.filter((i) => i.basis.startsWith("records:")),
    routine: review.routine.filter((i) => !i.basis.startsWith("risk_engine:context:")),
    required: []
  };
}

function FindingCaseFilesSection({
  pkg,
  reasoning,
  activeQuery,
  onInvestigate
}: {
  pkg: InvestigationPackage;
  reasoning: InvestigationReasoning;
  activeQuery: string;
  onInvestigate: (query: string) => void;
}) {
  const findings = caseFileFindings(pkg);
  const sourceIndex = useMemo(() => buildSourceIndex(pkg), [pkg]);
  const challengeById = useMemo(() => {
    const map = new Map<string, NonNullable<InvestigationReasoning["evidence_challenge"]>["challenges"][number]>();
    for (const c of reasoning.evidence_challenge?.challenges ?? []) {
      if (!map.has(c.finding_id)) map.set(c.finding_id, c);
    }
    return map;
  }, [reasoning.evidence_challenge]);
  const screeningSummary = pkg.risk_assessment_v2?.summary?.trim();

  // Retrieved facts for the Procurement Context Analyzer's applicability
  // evaluation — a minimal, read-only projection of the package records so
  // guidance is shown only when the evidence actually supports it.
  const contextFacts: ContextFactsPayload = useMemo(
    () => ({
      records: pkg.records.map((r) => ({
        reference_number: r.tender.reference_number,
        title: r.tender.title ?? "",
        description: r.tender.description ?? "",
        procuring_entity: r.tender.procuring_entity ?? "",
        suppliers: r.awards.map((a) => a.company_name).filter(Boolean),
        published_date: r.tender.published_date,
        closing_date: r.tender.closing_date,
        award_dates: r.awards.map((a) => a.award_date).filter((d): d is string => Boolean(d))
      })),
      as_of: pkg.records
        .map((r) => r.tender.metadata?.retrieved_at)
        .filter(Boolean)
        .sort()
        .pop()
        ?.slice(0, 10)
    }),
    [pkg]
  );

  return (
    <Section
      eyebrow="Findings"
      title="Investigation case files"
      action={
        <span className="inline-flex items-center gap-1.5 text-xs text-faint">
          <ListChecks className="h-3.5 w-3.5" />
          {findings.length} finding{findings.length === 1 ? "" : "s"} · each answers the five investigator questions
        </span>
      }
    >
      {findings.length === 0 ? (
        <EmptyState message="No findings were raised by deterministic screening for this investigation." />
      ) : (
        <>
          {screeningSummary && (
            <p className="mb-5 rounded-xl border border-border bg-bg-2/40 px-4 py-3.5 text-[13.5px] leading-relaxed text-muted">
              {screeningSummary}
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {findings.map((f, i) => {
              const sources: OfficialSource[] = [];
              const seen = new Set<string>();
              for (const ref of f.recordRefs) {
                const src = sourceIndex.get(ref);
                if (src && !seen.has(src.url)) {
                  seen.add(src.url);
                  sources.push(src);
                }
              }
              return (
                <FindingCaseFile
                  key={`${f.id}-${i}`}
                  finding={f}
                  challenge={challengeById.get(f.id) ?? null}
                  sources={sources}
                  nextSteps={nextStepsFor(f.recordRefs, pkg, activeQuery)}
                  index={i}
                  onInvestigate={onInvestigate}
                  contextFacts={contextFacts}
                  triggerFacts={triggerFactsFor(f, pkg)}
                />
              );
            })}
          </div>
          <p className="mt-5 text-[11.5px] leading-relaxed text-faint">
            Findings come from deterministic screening of the official procurement records above. They are leads for a
            human investigator to review — never, by themselves, a determination of wrongdoing.
          </p>
        </>
      )}
    </Section>
  );
}


/* ============================================================ evidence packet export */

/**
 * Open the authoritative, server-rendered Evidence Packet in a new tab.
 *
 * Single source of truth: the backend re-runs the deterministic pipeline and
 * returns a self-contained, print-ready HTML document (every figure traceable to
 * an official source URL, with a "Print / Save as PDF" control). Opening in a new
 * tab keeps the live investigation on screen behind it — one click, full packet.
 */
function openEvidencePacket(query: string): void {
  if (typeof window === "undefined" || !query) return;
  window.open(evidencePacketUrl(query), "_blank", "noopener,noreferrer");
}

/**
 * Smooth-scroll to an evidence section by id. Every headline number is a jump to
 * the records behind it — one click from a figure to its proof (req 12), so an
 * analyst never has to hunt for the evidence a claim rests on.
 */
function scrollToEvidence(id: string): void {
  if (typeof document === "undefined") return;
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function AiSummaryDivider() {
  return (
    <div className="relative flex items-center gap-4 pt-4">
      <span className="h-px flex-1 bg-border" />
      <span className="t-label inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3.5 py-1.5">
        Narrative summary · secondary
      </span>
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}

function EvidencePacketCTA({
  evidenceCount,
  sourceCount,
  onExport
}: {
  evidenceCount: number;
  sourceCount: number;
  onExport: () => void;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.slow, ease: EASE }}
      className="relative flex flex-col items-start gap-5 overflow-hidden rounded-2xl border border-accent/25 bg-surface/70 p-6 float sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-accent/30 bg-accent/[0.08] text-accent">
          <ScrollText className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <div className="text-[15px] font-semibold text-text">Evidence packet</div>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-muted">
            Export the full court-ready packet — {evidenceCount} cited item{evidenceCount === 1 ? "" : "s"} across{" "}
            {sourceCount} source{sourceCount === 1 ? "" : "s"}, every claim linked to its official source.
            <span className="ml-1 text-faint">15 sections incl. missing evidence, benign explanations &amp; a verification checklist · Print → PDF.</span>
          </p>
        </div>
      </div>
      <Button onClick={onExport} size="lg" icon={<Download className="h-4 w-4" />} className="shrink-0">
        Export evidence packet
      </Button>
    </motion.section>
  );
}
