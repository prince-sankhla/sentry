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
  ShieldCheck,
  Siren,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Chip } from "@/components/ui/chip";
import { Section } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";

type FocusKey = "records" | "news" | "legal" | "compliance";

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

type SearchResult = {
  title: string;
  url: string;
  snippet?: string | null;
  source: string;
  published_date?: string | null;
};

type FocusState = {
  status: "queued" | "searching" | "complete" | "error";
  detail?: string;
  items: ContextItem[];
};

type IntelligenceResponse = {
  clusters: Array<{
    cluster: string;
    items: ContextItem[];
  }>;
};

const FOCUSES: Array<{ key: FocusKey; label: string; icon: typeof FileSearch }> = [
  { key: "records", label: "Tender / award / contract history", icon: FileSearch },
  { key: "news", label: "Current + past procurement reporting", icon: Newspaper },
  { key: "legal", label: "Litigation / court / tribunal context", icon: Scale },
  { key: "compliance", label: "Audit / vigilance / debarment signals", icon: Siren },
];

function createEmptyFocusState(): Record<FocusKey, FocusState> {
  return {
    records: { status: "queued", items: [] },
    news: { status: "queued", items: [] },
    legal: { status: "queued", items: [] },
    compliance: { status: "queued", items: [] },
  };
}

export function InvestigationWebResearch({ initialQuery }: { initialQuery: string }) {
  const emptyState = useMemo(createEmptyFocusState, []);
  const [focusState, setFocusState] = useState<Record<FocusKey, FocusState>>(emptyState);
  const [items, setItems] = useState<ContextItem[]>([]);
  const [running, setRunning] = useState(Boolean(initialQuery));
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!initialQuery) return;
    let alive = true;
    const controller = new AbortController();

    async function run() {
      setRunning(true);
      setRefreshing(false);
      setItems([]);
      setFocusState(createEmptyFocusState());

      const collect = async (focus: (typeof FOCUSES)[number], index: number) => {
        const detail = [
          "Searching the public web and procurement index…",
          "Collecting source pages and historical context…",
          "Cross-checking reporting, legal and regulatory context…",
          "Preserving source snapshots for analyst review…",
        ][index];
        setFocusState((prev) => ({
          ...prev,
          [focus.key]: { status: "searching", detail, items: [] },
        }));
        try {
          const response = await fetch("/api/web/context-search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: initialQuery, focus: focus.label, limit: 8 }),
            signal: controller.signal,
          });
          const payload = (await response.json()) as {
            stored_pages?: ContextItem[];
            context_items?: ContextItem[];
            search_results?: SearchResult[];
            detail?: string;
          };
          if (!response.ok) throw new Error(payload.detail || "Web search failed");
          const next = payload.context_items?.length
            ? payload.context_items
            : payload.stored_pages?.length
              ? payload.stored_pages
              : (payload.search_results ?? []).map((result, resultIndex) => searchResultToContext(result, focus.key, resultIndex));
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

      await Promise.allSettled(FOCUSES.map(collect));
      if (!alive) return;

      setRefreshing(true);
      try {
        const response = await fetch(`/api/web/context?q=${encodeURIComponent(initialQuery)}`, {
          signal: controller.signal,
        });
        if (response.ok) {
          const payload = (await response.json()) as IntelligenceResponse;
          const refreshed = payload.clusters.flatMap((cluster) => cluster.items ?? []);
          if (alive) setItems((prev) => mergeItems(prev, refreshed));
        }
      } catch {
        // Context refresh is supplemental; collected results remain usable.
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
  }, [emptyState, initialQuery]);

  return (
    <Section
      eyebrow="Parallel intelligence"
      title="Open-web context research"
      action={
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.12em] text-faint">
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" /> : <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
          {running ? "Searching live" : refreshing ? "Refreshing snapshot" : "Research complete"}
        </div>
      }
    >
      <div className="mb-4 overflow-hidden rounded-xl border border-border bg-bg-2/40 p-4">
        <div className="flex items-start gap-3">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-accent/20 bg-accent/10 text-accent">
            <Globe2 className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold text-text">SENTRY is researching beyond the procurement record</div>
            <p className="mt-1 text-[11px] leading-5 text-muted">
              SENTRY searches the public web automatically across procurement, reporting, legal and compliance context. Web context is not treated as proof or allowed to change deterministic risk.
            </p>
          </div>
          <Sparkles className="hidden h-4 w-4 shrink-0 text-accent sm:block" />
        </div>
        {running && <div className="mt-4 h-1 overflow-hidden rounded-full bg-border"><motion.div className="h-full w-1/3 rounded-full bg-accent" animate={{ x: ["-120%", "360%"] }} transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }} /></div>}
      </div>

      <div className="grid gap-2 md:grid-cols-2">
        {FOCUSES.map(({ key, label, icon: Icon }) => {
          const state = focusState[key];
          return (
            <div key={key} className="rounded-xl border border-border bg-surface p-3">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-accent" />
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-text">{label}</span>
                {state.status === "searching" ? <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" /> : state.status === "complete" ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : null}
              </div>
              <div className="mt-2 text-[10px] text-faint">{state.detail ?? `${state.items.length} context items`}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 space-y-2">
        {items.length === 0 && !running ? (
          <EmptyState title="No web context found" message="No contextual web records were returned for this investigation query." />
        ) : (
          <AnimatePresence initial={false}>
            {items.slice(0, 16).map((item) => (
              <motion.article key={item.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-border p-3">
                <div className="flex items-start gap-3">
                  <Archive className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-text">{item.source}</span>
                      <Chip>{item.evidence_type}</Chip>
                      <Chip>{item.confidence_tier}</Chip>
                    </div>
                    <p className="mt-1 text-[11px] leading-5 text-muted">{item.evidence_summary}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-faint">
                      {item.id.startsWith("search-") ? null : <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3" /> SENTRY snapshot preserved</span>}
                      <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-accent hover:underline"><Link2 className="h-3 w-3" /> Original source</a>
                    </div>
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        )}
      </div>
    </Section>
  );
}

function searchResultToContext(result: SearchResult, focus: FocusKey, index: number): ContextItem {
  return {
    id: `search-${focus}-${index}-${result.url}`,
    source: result.source,
    source_type: "public_web_search",
    evidence_type: "Web Context",
    cluster: focus,
    confidence: 0.5,
    confidence_tier: "SEARCH RESULT",
    publication_date: result.published_date ?? null,
    url: result.url,
    evidence_summary: result.snippet || result.title,
    retrieved_at: new Date().toISOString(),
  };
}

function mergeItems(current: ContextItem[], incoming: ContextItem[]) {
  const map = new Map(current.map((item) => [item.id, item]));
  for (const item of incoming) map.set(item.id, item);
  return Array.from(map.values());
}
