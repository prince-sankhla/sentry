"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  CheckCircle2,
  FileSearch,
  Globe2,
  Link2,
  Loader2,
  Newspaper,
  Scale,
  Search,
  ShieldCheck,
  Siren,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Chip } from "@/components/ui/chip";
import { Section } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import type { ProcurementIntelligenceResponse } from "@/lib/api";

const FOCUSES = [
  { key: "records", label: "Tender / award / contract history", icon: FileSearch },
  { key: "news", label: "Current + past procurement reporting", icon: Newspaper },
  { key: "legal", label: "Litigation / court / tribunal context", icon: Scale },
  { key: "compliance", label: "Audit / vigilance / debarment signals", icon: Siren },
] as const;

type FocusKey = (typeof FOCUSES)[number]["key"];

type ContextItem = {
  id: string;
  source: string;
  source_type: string;
  evidence_type: string;
  cluster: string;
  confidence: number;
  confidence_tier: string;
  publication_date: string | null;
  url: string;
  evidence_summary: string;
  retrieved_at: string;
};

type FocusState = {
  status: "queued" | "searching" | "complete" | "error";
  detail?: string;
  items: ContextItem[];
};

export function InvestigationWebResearch({ initialQuery }: { initialQuery: string }) {
  const [focusState, setFocusState] = useState<Record<FocusKey, FocusState>>(() =>
    Object.fromEntries(FOCUSES.map(({ key }) => [key, { status: "queued", items: [] }])) as Record<FocusKey, FocusState>,
  );
  const [items, setItems] = useState<ContextItem[]>([]);
  const [running, setRunning] = useState(Boolean(initialQuery));
  const [refreshing, setRefreshing] = useState(false);
  const [pulse, setPulse] = useState(0);

  useEffect(() => {
    if (!initialQuery) return;
    let alive = true;
    const controller = new AbortController();

    async function run() {
      setRunning(true);
      setRefreshing(false);
      setItems([]);
      setFocusState(Object.fromEntries(FOCUSES.map(({ key }) => [key, { status: "queued", items: [] }])) as Record<FocusKey, FocusState>);

      const collect = async (focus: (typeof FOCUSES)[number], index: number) => {
        const detail = [
          "Searching indexed procurement pages…",
          "Collecting source pages and historical context…",
          "Classifying what is a record versus contextual reporting…",
          "Preserving a stable SENTRY snapshot for review…",
        ][index];
        setFocusState((prev) => ({ ...prev, [focus.key]: { status: "searching", detail, items: [] } }));
        try {
          const response = await fetch("/api/web/context-search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: initialQuery, focus: focus.label, limit: 8 }),
            signal: controller.signal,
          });
          const payload = (await response.json()) as { stored_pages?: ContextItem[]; error?: string };
          if (!response.ok) throw new Error(payload.error || "Web search failed");
          const next = payload.stored_pages ?? [];
          if (!alive) return;
          setFocusState((prev) => ({ ...prev, [focus.key]: { status: "complete", items: next } }));
          setItems((prev) => mergeItems(prev, next));
        } catch (error) {
          if (controller.signal.aborted || !alive) return;
          setFocusState((prev) => ({
            ...prev,
            [focus.key]: {
              status: "error",
              detail: error instanceof Error ? error.message : "Web search failed",
              items: [],
            },
          }));
        }
      };

      // Run all four research lanes in parallel so the live panel genuinely
      // behaves like a parallel investigation rather than a staged animation.
      await Promise.allSettled(FOCUSES.map(collect));
      if (!alive) return;

      setRefreshing(true);
      try {
        const response = await fetch(`/api/web/context?q=${encodeURIComponent(initialQuery)}&limit=80`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.ok) {
          const intelligence = (await response.json()) as ProcurementIntelligenceResponse;
          const flattened = intelligence.clusters.flatMap((cluster) => cluster.items.map((item) => ({
            id: item.id,
            source: item.source,
            source_type: item.source_type,
            evidence_type: item.evidence_type,
            cluster: item.cluster,
            confidence: item.confidence,
            confidence_tier: item.confidence_tier,
            publication_date: item.publication_date,
            url: item.url,
            evidence_summary: item.evidence_summary,
            retrieved_at: item.retrieved_at,
          })));
          setItems(flattened);
        }
      } catch {
        // Existing collected cards remain visible even when the aggregate read fails.
      } finally {
        if (alive) {
          setRefreshing(false);
          setRunning(false);
        }
      }
    }

    void run();
    return () => {
      alive = false;
      controller.abort();
    };
  }, [initialQuery]);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setPulse((value) => value + 1), 1400);
    return () => window.clearInterval(timer);
  }, [running]);

  const completed = FOCUSES.filter(({ key }) => focusState[key].status === "complete").length;
  const failed = FOCUSES.filter(({ key }) => focusState[key].status === "error").length;
  const progress = running ? Math.max(8, Math.round(((completed + failed) / FOCUSES.length) * 100)) : 100;
  const clusters = useMemo(() => countClusters(items), [items, pulse]);

  return (
    <section className="mt-8">
      <Section
        eyebrow="Parallel intelligence"
        title="Open-web context is being researched alongside the procurement investigation"
        action={
          <span className="inline-flex items-center gap-2 text-[11px] text-faint">
            <span className={`h-1.5 w-1.5 rounded-full ${running ? "bg-accent pulse-live" : "bg-success"}`} />
            {running ? "Searching live" : "Research pass complete"}
          </span>
        }
      >
        <div className="rounded-2xl border border-border bg-bg-2/50 p-4 sm:p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.15em] text-accent">
                <Globe2 className="h-3.5 w-3.5" />
                Web intelligence console
              </div>
              <div className="mt-2 flex items-center gap-2.5">
                {running ? <Loader2 className="h-5 w-5 animate-spin text-accent" /> : <CheckCircle2 className="h-5 w-5 text-success" />}
                <div>
                  <div className="text-sm font-semibold text-text">{running ? "SENTRY is searching beyond the structured dataset" : "Context research assembled"}</div>
                  <div className="mt-0.5 text-xs text-muted">
                    {running ? "Collecting tender history, contracts, reporting, legal context and integrity signals…" : `${items.length} admissible context items retained for review.`}
                  </div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 lg:min-w-[280px]">
              <MiniStat label="Lanes complete" value={`${completed}/${FOCUSES.length}`} />
              <MiniStat label="Context items" value={items.length} />
              <MiniStat label="Progress" value={`${progress}%`} />
            </div>
          </div>

          <div className="mt-5 h-1 overflow-hidden rounded-full bg-border">
            <motion.div className="h-full bg-accent" animate={{ width: `${progress}%` }} transition={{ duration: 0.35 }} />
          </div>

          <div className="mt-5 grid gap-2 md:grid-cols-2">
            {FOCUSES.map((focus) => {
              const state = focusState[focus.key];
              const Icon = focus.icon;
              return (
                <div key={focus.key} className="flex items-center gap-3 rounded-xl border border-border bg-surface/60 px-3.5 py-3">
                  <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border ${state.status === "complete" ? "border-success/25 bg-success/10 text-success" : state.status === "error" ? "border-danger/25 bg-danger/10 text-danger" : "border-accent/25 bg-accent/10 text-accent"}`}>
                    {state.status === "complete" ? <CheckCircle2 className="h-4 w-4" /> : state.status === "searching" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-text">{focus.label}</div>
                    <div className="mt-0.5 truncate text-[10.5px] text-faint">{state.detail ?? (state.status === "queued" ? "Queued" : `${state.items.length} sources retained`)}</div>
                  </div>
                  <Chip tone={state.status === "complete" ? "success" : state.status === "error" ? "danger" : "neutral"}>
                    {state.status === "complete" ? `${state.items.length} found` : state.status === "searching" ? "searching" : state.status}
                  </Chip>
                </div>
              );
            })}
          </div>
        </div>

        <AnimatePresence>
          {items.length > 0 ? (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-text">Context signals to inspect</div>
                  <div className="mt-0.5 text-[11px] text-muted">These sources can corroborate timelines, surface prior reporting, locate documents, or challenge an explanation. They do not modify the deterministic risk result.</div>
                </div>
                <div className="hidden items-center gap-1.5 sm:flex">
                  {clusters.map((cluster) => <Chip key={cluster.key} tone="neutral">{cluster.label} · {cluster.count}</Chip>)}
                </div>
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                {items.slice(0, 12).map((item) => <ContextCard key={item.id} item={item} />)}
              </div>
              {items.length > 12 ? <div className="mt-3 text-center text-[10.5px] text-faint">+{items.length - 12} additional context items available in the research workspace.</div> : null}
            </motion.div>
          ) : !running ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5">
              <EmptyState icon={<Sparkles className="h-5 w-5" />} title="No admissible web context found" message="The absence of web context is not evidence of an issue. Try Guided Research for a more targeted source query." />
            </motion.div>
          ) : null}
        </AnimatePresence>

        <div className="mt-5 flex flex-col gap-2 rounded-xl border border-warning/20 bg-warning/[0.04] px-4 py-3 text-[11px] leading-relaxed text-muted sm:flex-row sm:items-start">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <div>
            <span className="font-semibold text-text">Context only — not procurement evidence.</span> Open-web material stays separate from official procurement records and deterministic risk calculations. SENTRY captures a review snapshot so the investigator is not dependent on a source session remaining valid.
            {refreshing ? <span className="ml-1 text-faint">Refreshing the aggregate context view…</span> : null}
          </div>
        </div>
      </Section>
    </section>
  );
}

function ContextCard({ item }: { item: ContextItem }) {
  const archiveUrl = `/api/web/archive/${item.id}`;
  const date = item.publication_date ? formatDate(item.publication_date) : `retrieved ${formatDate(item.retrieved_at)}`;
  return (
    <article className="group rounded-2xl border border-border bg-surface/70 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-border-strong">
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent"><Archive className="h-4 w-4" /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Chip tone="neutral">{item.evidence_type.replaceAll("_", " ")}</Chip>
            <Chip tone="outline">{item.source_type.replaceAll("_", " ")}</Chip>
            <span className="text-[10px] text-faint">{date}</span>
          </div>
          <h3 className="mt-2 text-[13px] font-semibold leading-snug text-text">{item.evidence_summary}</h3>
          <div className="mt-1 truncate text-[10.5px] text-faint">{item.source}</div>
        </div>
        <span className="hidden shrink-0 tabular text-[10px] font-semibold text-muted sm:block">{Math.round(item.confidence * 100)}%</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3">
        <a href={archiveUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-accent/25 bg-accent/[0.06] px-2.5 py-1.5 text-[10.5px] font-medium text-accent transition hover:bg-accent/10">
          <Archive className="h-3.5 w-3.5" /> SENTRY snapshot
        </a>
        <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/50 px-2.5 py-1.5 text-[10.5px] font-medium text-muted transition hover:text-text">
          <Link2 className="h-3.5 w-3.5" /> Original source
        </a>
      </div>
    </article>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-xl border border-border bg-surface/70 px-3 py-2.5"><div className="t-label">{label}</div><div className="mt-1 text-sm font-semibold tabular text-text">{value}</div></div>;
}

function mergeItems(current: ContextItem[], next: ContextItem[]) {
  const merged = new Map<string, ContextItem>();
  [...current, ...next].forEach((item) => merged.set(item.id, item));
  return Array.from(merged.values()).slice(0, 80);
}

function countClusters(items: ContextItem[]) {
  const labels: Record<string, string> = {
    contracts: "Contracts",
    litigation: "Litigation",
    audit: "Audit",
    compliance: "Compliance",
    financial: "Financial",
    news: "News",
    government: "Government",
  };
  const counts = new Map<string, number>();
  items.forEach((item) => counts.set(item.cluster, (counts.get(item.cluster) ?? 0) + 1));
  return Array.from(counts.entries()).map(([key, count]) => ({ key, count, label: labels[key] ?? key }));
}

function formatDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(parsed);
}
