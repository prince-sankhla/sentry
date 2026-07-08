"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
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
  Network,
  RotateCcw,
  Search,
  Sparkles,
  X
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { RelationshipGraphExplorer } from "@/app/graph/relationship-graph";
import { CommandCenter } from "@/app/command-center";
import { EvidenceCard, type EvidenceItem } from "@/components/intel/evidence-card";
import { AiInvestigationPanel } from "@/components/intel/ai-investigation-panel";
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
  type InvestigationPackage,
  type InvestigationProcurementRecord,
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

/* ============================================================ graph builder */

function buildGraphFromRecords(records: InvestigationProcurementRecord[]): RelationshipGraph {
  const nodes = new Map<string, RelationshipGraph["nodes"][number]>();
  const edges: RelationshipGraph["edges"] = [];
  const addNode = (n: RelationshipGraph["nodes"][number]) => {
    if (!nodes.has(n.id)) nodes.set(n.id, n);
  };
  const addEdge = (e: RelationshipGraph["edges"][number]) => {
    if (!edges.some((x) => x.id === e.id)) edges.push(e);
  };

  for (const r of records) {
    const t = r.tender;
    const tId = `t:${t.reference_number}`;
    addNode({
      id: tId,
      type: "tender",
      label: t.title || t.reference_number,
      data: {
        reference_number: t.reference_number,
        buyer: t.procuring_entity,
        estimated_value: t.estimated_value,
        currency: t.currency,
        published_date: t.published_date,
        source: t.metadata?.source_name
      }
    });

    if (t.procuring_entity) {
      const bId = `b:${t.procuring_entity.toLowerCase()}`;
      addNode({ id: bId, type: "buyer", label: t.procuring_entity, data: { role: "Procuring entity" } });
      addEdge({ id: `${bId}->${tId}`, source: bId, target: tId, type: "buyer_tender", label: "issued", data: {} });
    }

    for (const c of r.companies) {
      const cId = `c:${c.name.toLowerCase()}`;
      addNode({
        id: cId,
        type: "company",
        label: c.name,
        data: { registration_number: c.registration_number, source: c.metadata?.source_name }
      });
      addEdge({ id: `${cId}~${tId}`, source: cId, target: tId, type: "company_tender", label: "participated", data: {} });
    }

    for (const a of r.awards) {
      const cId = `c:${a.company_name.toLowerCase()}`;
      addNode({ id: cId, type: "company", label: a.company_name, data: { registration_number: a.company_registration_number } });
      addEdge({
        id: `${tId}=>${cId}`,
        source: tId,
        target: cId,
        type: "tender_award",
        label: a.award_value ? formatCompactMoney(a.award_value, a.currency) : "awarded",
        data: { award_value: a.award_value, currency: a.currency, award_date: a.award_date }
      });
    }
  }

  return { nodes: [...nodes.values()], edges };
}

/* ============================================================ root */

export function InvestigationWorkspace({ initialQuery }: { initialQuery: string }) {
  const router = useRouter();
  const [input, setInput] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [steps, setSteps] = useState<Step[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pkg, setPkg] = useState<InvestigationPackage | null>(null);
  const [reasoning, setReasoning] = useState<InvestigationReasoning | null>(null);
  const [graph, setGraph] = useState<RelationshipGraph | null>(null);
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
      onReport: (report) => {
        if (startedAtRef.current != null) setProcessingMs(performance.now() - startedAtRef.current);
        setPkg(report.package);
        setReasoning(report.reasoning);
        setGraph(buildGraphFromRecords(report.package.records));
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

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setActiveQuery(q);
    router.push(`/?q=${encodeURIComponent(q)}`);
    runInvestigation(q);
  }

  const launchFollowUp = useCallback(
    (query: string) => {
      setInput(query);
      setActiveQuery(query);
      router.push(`/?q=${encodeURIComponent(query)}`);
      runInvestigation(query);
    },
    [router, runInvestigation]
  );

  function reset() {
    abortRef.current?.();
    setInput("");
    setActiveQuery("");
    setPkg(null);
    setReasoning(null);
    setGraph(null);
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
      <WorkspaceSearch
        input={input}
        setInput={setInput}
        onSubmit={submit}
        activeQuery={activeQuery}
        running={running}
        onReset={reset}
        providerStatus={providerStatus}
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

/* ============================================================ search bar */

function WorkspaceSearch({
  input,
  setInput,
  onSubmit,
  activeQuery,
  running,
  onReset,
  providerStatus
}: {
  input: string;
  setInput: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  activeQuery: string;
  running: boolean;
  onReset: () => void;
  providerStatus: LLMProviderStatus | null;
}) {
  return (
    <div className="animate-rise">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          <Sparkles className="h-3.5 w-3.5" /> AI Investigation Workspace
        </div>
        {providerStatus && (
          <ProviderBadge
            generatedBy={providerStatus.mode === "llm" ? "llm" : "deterministic"}
            provider={providerStatus.providers[0]}
          />
        )}
      </div>
      <form onSubmit={onSubmit} className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Investigate an entity, e.g. “Find suspicious road tenders in Rajasthan”"
            className="h-12 w-full rounded-xl border border-border bg-surface pl-11 pr-4 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/60"
          />
        </div>
        <button
          type="submit"
          disabled={running}
          className="flex h-12 items-center justify-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-bg transition hover:bg-accent-hi disabled:opacity-60"
        >
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
          {running ? "Investigating" : "Investigate"}
        </button>
        {activeQuery && (
          <button
            type="button"
            onClick={onReset}
            aria-label="Reset investigation"
            title="Reset investigation"
            className="flex h-12 items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 text-sm text-muted transition hover:text-text"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
      </form>
      {activeQuery && (
        <div className="mt-3 flex items-center gap-2 text-sm text-muted">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-accent">
            {activeQuery}
            <button type="button" onClick={onReset} aria-label="Clear">
              <X className="h-3 w-3" />
            </button>
          </span>
        </div>
      )}
      <div className="rule mt-5" />
    </div>
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
  webPages: StoredWebPage[];
  onWebSearch: () => void;
  webBusy: boolean;
  onFollowUp: (query: string) => void;
  processingMs: number | null;
}) {
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

  return (
    <div className="mt-6 space-y-5">
      {/* Flagship AI investigation panel — always shown, even when insufficient */}
      <AiInvestigationPanel reasoning={reasoning} processingMs={processingMs} />

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

          {/* graph */}
          <Section
            eyebrow="Network"
            title="Relationship graph"
            action={
              <span className="inline-flex items-center gap-1.5 text-xs text-faint">
                <Network className="h-3.5 w-3.5" />
                {graph?.nodes.length ?? 0} nodes · {graph?.edges.length ?? 0} edges
              </span>
            }
          >
            {graph && graph.nodes.length > 0 ? (
              <div className="h-[520px] overflow-hidden rounded-[14px] border border-border">
                <RelationshipGraphExplorer graph={graph} />
              </div>
            ) : (
              <EmptyState message="No relationships could be built for this investigation." />
            )}
          </Section>

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
                    kind: "web"
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
