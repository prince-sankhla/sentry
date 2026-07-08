"use client";

/**
 * EvidenceLedger — SENTRY's flagship provenance surface.
 *
 * The complete, de-duplicated citation trail behind an investigation. Every card
 * exposes the full provenance the backend Evidence Engine already computes: a
 * quality score (★) and tier, a confidence read-out, the original source and URL,
 * an attached document/PDF, retrieval + publication timing, the related tender /
 * company, a one-click analyst-grade citation, and a plain-language explanation
 * of *why* the evidence is trusted. Sortable by quality, filterable by source,
 * Indian sources promoted. Nothing is invented — each field is read straight from
 * the grounded `ReasoningCitation`.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowUpDown,
  Building2,
  Check,
  ChevronDown,
  Copy,
  ExternalLink,
  FileText,
  Filter,
  Info,
  Star
} from "lucide-react";
import { useMemo, useState } from "react";
import type { EvidenceQualityTier, ReasoningCitation } from "@/lib/api";
import { bySourcePriority, isIndianSource, sourceMeta } from "@/lib/sources";

/* ---------------------------------------------------------------- tiers */

const TIER: Record<EvidenceQualityTier, { label: string; cls: string; dot: string }> = {
  primary: { label: "Primary", cls: "border-accent/40 bg-accent/[0.08] text-accent", dot: "bg-accent" },
  corroborating: { label: "Corroborating", cls: "border-info/40 bg-info/[0.08] text-info", dot: "bg-info" },
  weak: { label: "Weak", cls: "border-warning/40 bg-warning/[0.08] text-warning", dot: "bg-warning" },
  unverified: { label: "Unverified", cls: "border-border-strong bg-surface-2 text-faint", dot: "bg-faint" }
};

type SortKey = "quality" | "confidence" | "recent";

/* ---------------------------------------------------------------- helpers */

function fmtDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

function fmtDateTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(d);
}

function stars(quality: number): number {
  return Math.max(0, Math.min(5, Math.round(quality / 20)));
}

/** Compose a plain-language rationale for the evidence's trust level. */
function whyTrusted(c: ReasoningCitation): string[] {
  const reasons: string[] = [];
  const meta = sourceMeta(c.source_name);
  if (c.quality_tier === "primary") reasons.push(`Primary-tier source (${meta.label}) with high analyst authority.`);
  else if (c.quality_tier === "corroborating") reasons.push(`Corroborating source (${meta.label}) supporting the primary record.`);
  else if (c.quality_tier === "weak") reasons.push(`Weak signal from ${meta.label} — treat as supplementary.`);
  else reasons.push(`Unverified reference from ${meta.label} — provenance incomplete.`);

  if (c.source_url) reasons.push("Original source is publicly linkable and independently verifiable.");
  if (c.document_url) reasons.push("An original document / PDF is attached for direct inspection.");
  if (isIndianSource(c.source_name)) reasons.push("Prioritised Indian procurement source.");
  if (c.published_date) reasons.push(`Publication date on record (${fmtDate(c.published_date)}).`);
  if (!c.source_url && !c.document_url) reasons.push("No public URL — cited by stable source record id.");
  return reasons;
}

function buildCitationText(c: ReasoningCitation): string {
  if (c.citation && c.citation.trim()) return c.citation.trim();
  const meta = sourceMeta(c.source_name);
  const parts = [c.label.trim(), meta.label];
  if (c.related_tender) parts.push(`Ref ${c.related_tender}`);
  if (c.published_date) parts.push(fmtDate(c.published_date));
  const url = c.source_url ?? c.document_url;
  if (url) parts.push(url);
  return `${parts.join(". ")}. (confidence ${Math.round(c.confidence * 100)}%) — Retrieved via SENTRY.`;
}

/* ---------------------------------------------------------------- container */

export function EvidenceLedger({ items }: { items: ReasoningCitation[] }) {
  const [sort, setSort] = useState<SortKey>("quality");
  const [source, setSource] = useState<string>("all");

  const sources = useMemo(() => {
    const uniq = new Map<string, string>();
    for (const c of items) uniq.set(c.source_name.toLowerCase(), c.source_name);
    return bySourcePriority([...uniq.values()], (s) => s);
  }, [items]);

  const shown = useMemo(() => {
    const filtered = source === "all" ? items : items.filter((c) => c.source_name.toLowerCase() === source);
    const sorted = [...filtered];
    if (sort === "quality") sorted.sort((a, b) => b.quality - a.quality);
    else if (sort === "confidence") sorted.sort((a, b) => b.confidence - a.confidence);
    else
      sorted.sort((a, b) => {
        const ta = a.retrieved_at ? new Date(a.retrieved_at).getTime() : 0;
        const tb = b.retrieved_at ? new Date(b.retrieved_at).getTime() : 0;
        return tb - ta;
      });
    return sorted;
  }, [items, source, sort]);

  if (items.length === 0) return null;

  return (
    <div>
      {/* toolbar */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="mr-auto inline-flex items-center gap-1.5 text-[11px] text-faint">
          <Filter className="h-3.5 w-3.5" /> {shown.length} of {items.length} evidence items
        </span>

        {/* source filter */}
        <div className="flex flex-wrap items-center gap-1">
          <FilterChip active={source === "all"} onClick={() => setSource("all")} label="All sources" />
          {sources.map((s) => (
            <FilterChip
              key={s}
              active={source === s.toLowerCase()}
              onClick={() => setSource(s.toLowerCase())}
              label={sourceMeta(s).short}
              indian={isIndianSource(s)}
            />
          ))}
        </div>

        {/* sort */}
        <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface p-0.5">
          <ArrowUpDown className="ml-1.5 h-3 w-3 text-faint" />
          {(["quality", "confidence", "recent"] as SortKey[]).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setSort(k)}
              className={`rounded-md px-2 py-1 text-[11px] font-medium capitalize transition ${
                sort === k ? "bg-accent/15 text-accent" : "text-muted hover:text-text"
              }`}
            >
              {k}
            </button>
          ))}
        </div>
      </div>

      {/* grid */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <AnimatePresence mode="popLayout">
          {shown.map((c, i) => (
            <LedgerCard key={`${c.source_name}:${c.source_record_id ?? c.label}:${i}`} citation={c} index={i} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  label,
  indian
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  indian?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
        active
          ? "border-accent/50 bg-accent/[0.1] text-accent"
          : "border-border bg-surface text-muted hover:border-border-strong hover:text-text"
      }`}
    >
      {indian && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
      {label}
    </button>
  );
}

/* ---------------------------------------------------------------- card */

function LedgerCard({ citation: c, index }: { citation: ReasoningCitation; index: number }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const tier = TIER[c.quality_tier];
  const meta = sourceMeta(c.source_name);
  const indian = isIndianSource(c.source_name);
  const filled = stars(c.quality);

  async function copyCitation() {
    try {
      await navigator.clipboard.writeText(buildCitationText(c));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ delay: Math.min(index, 10) * 0.03, duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className={`group relative flex flex-col overflow-hidden rounded-[16px] border bg-surface/70 transition-colors hover:border-border-strong ${
        indian ? "border-l-2 border-l-accent/60 border-y-border border-r-border" : "border-border"
      }`}
    >
      {/* header: source + tier */}
      <div className="flex items-center gap-2 border-b border-border/60 bg-bg-2/30 px-3.5 py-2.5">
        <span
          className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${
            indian ? "border-accent/30 bg-accent/[0.08] text-accent" : "border-border bg-bg-2 text-muted"
          }`}
        >
          <FileText className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-muted">{meta.label}</span>
        <span className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${tier.cls}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${tier.dot}`} />
          {tier.label}
        </span>
      </div>

      <div className="flex flex-1 flex-col p-3.5">
        {/* quality stars + confidence */}
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-0.5" title={`Quality ${c.quality}/100`}>
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                className={`h-3.5 w-3.5 ${i < filled ? "fill-accent text-accent" : "text-border-strong"}`}
              />
            ))}
            <span className="ml-1 tabular text-[10px] text-faint">{c.quality}</span>
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] text-muted">
            <span className={`h-1.5 w-1.5 rounded-full ${c.confidence >= 0.8 ? "bg-success" : c.confidence >= 0.5 ? "bg-warning" : "bg-faint"}`} />
            {Math.round(c.confidence * 100)}%
          </span>
        </div>

        {/* title */}
        <div className="line-clamp-2 text-sm font-medium text-text">{c.label}</div>

        {/* related links */}
        {(c.related_tender || c.related_entity) && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {c.related_tender && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/50 px-1.5 py-0.5 font-mono text-[10px] text-muted">
                <FileText className="h-2.5 w-2.5" /> {c.related_tender}
              </span>
            )}
            {c.related_entity && (
              <span className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/50 px-1.5 py-0.5 text-[10px] text-muted">
                <Building2 className="h-2.5 w-2.5" /> {c.related_entity}
              </span>
            )}
          </div>
        )}

        {/* dates */}
        <div className="mt-2.5 grid grid-cols-2 gap-2 text-[10px]">
          <div>
            <div className="uppercase tracking-wide text-faint">Retrieved</div>
            <div className="text-muted">{fmtDateTime(c.retrieved_at)}</div>
          </div>
          <div>
            <div className="uppercase tracking-wide text-faint">Published</div>
            <div className="text-muted">{fmtDate(c.published_date)}</div>
          </div>
        </div>

        {/* expandable metadata */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="mt-2.5 inline-flex items-center gap-1 self-start text-[11px] font-medium text-accent transition hover:text-accent-hi"
        >
          <ChevronDown className={`h-3.5 w-3.5 transition ${open ? "rotate-180" : ""}`} />
          {open ? "Hide" : "Why trusted"}
        </button>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="overflow-hidden"
            >
              <ul className="mt-2 space-y-1.5 rounded-lg border border-border bg-bg-2/40 p-2.5">
                {whyTrusted(c).map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-muted">
                    <Info className="mt-0.5 h-3 w-3 shrink-0 text-accent" />
                    <span>{r}</span>
                  </li>
                ))}
                <li className="flex items-start gap-1.5 border-t border-border/60 pt-1.5 text-[10px] text-faint">
                  <span className="font-mono">{c.evidence_type}</span>
                  {c.source_record_id && <span className="font-mono">· {c.source_record_id}</span>}
                </li>
              </ul>
            </motion.div>
          )}
        </AnimatePresence>

        {/* actions */}
        <div className="mt-3 flex items-center gap-1.5 border-t border-border/60 pt-2.5">
          {c.source_url ? (
            <a
              href={c.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/60 px-2 py-1 text-[11px] font-medium text-muted transition hover:border-accent/40 hover:text-accent"
            >
              <ExternalLink className="h-3 w-3" /> Original
            </a>
          ) : null}
          {c.document_url ? (
            <a
              href={c.document_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/60 px-2 py-1 text-[11px] font-medium text-muted transition hover:border-accent/40 hover:text-accent"
            >
              <FileText className="h-3 w-3" /> PDF
            </a>
          ) : null}
          {!c.source_url && !c.document_url && (
            <span className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/40 px-2 py-1 font-mono text-[10px] text-faint">
              {c.source_record_id ?? "No public URL"}
            </span>
          )}
          <button
            type="button"
            onClick={copyCitation}
            className="ml-auto inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/60 px-2 py-1 text-[11px] font-medium text-muted transition hover:border-accent/40 hover:text-accent"
            aria-label="Copy citation"
          >
            {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
            {copied ? "Copied" : "Cite"}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
