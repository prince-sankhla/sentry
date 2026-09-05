"use client";

/**
 * EvidenceCard — the canonical provenance surface for SENTRY.
 *
 * Wherever the platform asserts a fact (an investigation finding, a dossier
 * claim, a report citation) the underlying evidence renders through this card so
 * provenance is never hidden. Every card exposes: source name, a clickable
 * source URL, an archived SENTRY snapshot when a web capture exists, publication
 * date, a confidence read-out, and a one-click "copy citation".
 */

import { motion } from "framer-motion";
import {
  BadgeCheck,
  BriefcaseBusiness,
  Building2,
  Check,
  Copy,
  ExternalLink,
  FileText,
  Globe2,
  Landmark,
  ShieldCheck,
  Tags
} from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";
import { isIndianSource, sourceMeta } from "@/lib/sources";
import { DURATION, EASE } from "@/lib/motion";

export type EvidenceItem = {
  title: string;
  source: string;
  sourceUrl?: string | null;
  recordId?: string | null;
  date?: string | null;
  confidence?: number | null;
  detail?: string | null;
  reference?: string | null;
  kind?: "record" | "web" | "document";
  evidenceType?: string | null;
  citation?: string | null;
  relatedEntities?: string[];
  relatedContracts?: string[];
  relatedTenders?: string[];
  relatedOrganizations?: string[];
  tags?: string[];
  retrievedAt?: string | null;
  integrityHash?: string | null;
  /** Explicit archived/stable URL when the caller already knows the SENTRY snapshot. */
  archivedUrl?: string | null;
  /** Whether the original source URL is still reachable. */
  sourceAvailable?: boolean | null;
};

function fmtDate(value?: string | null): string {
  if (!value) return "Undated";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

function buildCitation(e: EvidenceItem): string {
  if (e.citation?.trim()) return e.citation.trim();
  const meta = sourceMeta(e.source);
  const parts = [e.title.trim()];
  parts.push(meta.label);
  if (e.reference) parts.push(`Ref ${e.reference}`);
  parts.push(fmtDate(e.date));
  if (e.sourceUrl) parts.push(e.sourceUrl);
  const conf = typeof e.confidence === "number" ? ` (confidence ${Math.round(e.confidence * 100)}%)` : "";
  return `${parts.join(". ")}.${conf} — Retrieved via SENTRY.`;
}

function confidenceTone(c: number): { label: string; cls: string } {
  if (c >= 0.8) return { label: "High confidence", cls: "text-success" };
  if (c >= 0.5) return { label: "Moderate confidence", cls: "text-warning" };
  return { label: "Low confidence", cls: "text-muted" };
}

export function EvidenceCard({ item, index = 0 }: { item: EvidenceItem; index?: number }) {
  const [copied, setCopied] = useState(false);
  const meta = sourceMeta(item.source);
  const indian = isIndianSource(item.source);
  const Glyph = item.kind === "web" ? Globe2 : item.kind === "document" ? FileText : ShieldCheck;
  const effectiveArchivedUrl =
    item.archivedUrl ??
    (item.kind === "web" && item.recordId
      ? `/api/web/archive/${encodeURIComponent(item.recordId)}`
      : item.kind === "web" && item.sourceUrl
        ? `/api/web/archive/by-url?source_url=${encodeURIComponent(item.sourceUrl)}`
        : null);

  async function copyCitation() {
    try {
      await navigator.clipboard.writeText(buildCitation(item));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable — no-op */
    }
  }

  const hasConf = typeof item.confidence === "number";
  const conf = hasConf ? confidenceTone(item.confidence as number) : null;
  const evidenceType = item.evidenceType ?? (item.kind === "web" ? "Open-source record" : item.kind === "document" ? "Document" : "Procurement record");

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 12) * 0.035, duration: DURATION.base, ease: EASE }}
      whileHover={{ y: -2 }}
      className={`group relative overflow-hidden rounded-xl border bg-surface/70 p-4 transition-colors duration-200 hover:border-border-strong ${
        indian ? "border-l-2 border-l-accent/60 border-y-border border-r-border" : "border-border"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg border ${indian ? "border-accent/30 bg-accent/[0.08] text-accent" : "border-border bg-bg-2 text-muted"}`}>
          <Glyph className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate text-[11.5px] font-medium text-muted">{meta.label}</span>
        <span className="shrink-0 rounded-md border border-border bg-bg-2/60 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-faint">{evidenceType}</span>
        {indian && <span className="shrink-0 rounded-md border border-accent/30 bg-accent/[0.08] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">India</span>}
      </div>

      <div className="mt-3">
        <div className="line-clamp-2 text-[13.5px] font-medium leading-relaxed text-text">{item.title}</div>
        {item.detail && <div className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted">{item.detail}</div>}
        {item.reference && <div className="mt-1.5 truncate font-mono text-[11px] text-faint">{item.reference}</div>}
      </div>

      <div className="mt-3.5 grid grid-cols-2 gap-2.5 text-[11px]">
        <MetaPill label="Published" value={fmtDate(item.date)} />
        {conf && <MetaPill label="Confidence" value={`${Math.round((item.confidence as number) * 100)}%`} valueClassName={conf.cls} />}
      </div>

      <div className="mt-3.5 space-y-2.5">
        <EvidenceChips icon={<Building2 className="h-3 w-3" />} label="Entities" items={item.relatedEntities} />
        <EvidenceChips icon={<BriefcaseBusiness className="h-3 w-3" />} label="Contracts" items={item.relatedContracts} />
        <EvidenceChips icon={<FileText className="h-3 w-3" />} label="Tenders" items={item.relatedTenders} />
        <EvidenceChips icon={<Landmark className="h-3 w-3" />} label="Organizations" items={item.relatedOrganizations} />
        <EvidenceChips icon={<Tags className="h-3 w-3" />} label="Tags" items={item.tags} tone="accent" />
      </div>

      {item.citation ? (
        <div className="mt-3.5 rounded-lg border border-border bg-bg-2/40 p-2.5 text-[11px] leading-relaxed text-muted">
          <span className="mb-1.5 flex items-center gap-1 font-semibold uppercase tracking-wide text-faint"><BadgeCheck className="h-3 w-3" />Citation</span>
          {item.citation}
        </div>
      ) : null}

      <div className="mt-3.5 border-t border-border/60 pt-3">
        {(item.sourceUrl || effectiveArchivedUrl) && (
          <div className="mb-2.5 flex flex-wrap items-center gap-2">
            {effectiveArchivedUrl && (
              <a
                href={effectiveArchivedUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-success/30 bg-success/[0.07] px-2.5 py-1.5 text-[11px] font-semibold text-success transition-colors duration-200 hover:bg-success/15"
              >
                <ShieldCheck className="h-3 w-3" />
                Open SENTRY Snapshot
              </a>
            )}
            {item.sourceUrl ? (
              <a
                href={item.sourceUrl}
                target="_blank"
                rel="noreferrer"
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition-colors duration-200 ${item.sourceAvailable === false ? "border-border bg-bg-2/40 text-faint line-through" : "border-border bg-bg-2/60 text-muted hover:border-accent/40 hover:text-accent"}`}
              >
                <ExternalLink className="h-3 w-3" />
                {item.sourceAvailable === false ? "Original unavailable" : "Open Original Source"}
              </a>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-lg border border-border bg-bg-2/40 px-2.5 py-1.5 font-mono text-[10px] text-faint">{item.recordId ?? "No public URL"}</span>
            )}
          </div>
        )}

        {(item.retrievedAt || item.integrityHash) && (
          <div className="mb-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10.5px] text-faint">
            {item.retrievedAt && (
              <span className="flex items-center gap-1"><span className="text-faint/60">Retrieved</span>{fmtDate(item.retrievedAt)}</span>
            )}
            {item.integrityHash && (
              <span className="flex items-center gap-1 font-mono" title={`SHA-256: ${item.integrityHash}`}>
                <span className="text-faint/60">SHA-256</span>
                {item.integrityHash.slice(0, 8)}…{item.integrityHash.slice(-6)}
                <span className="ml-0.5 rounded border border-success/20 bg-success/[0.06] px-1 py-px text-[9px] font-semibold uppercase tracking-wide text-success">verified</span>
              </span>
            )}
          </div>
        )}

        {!item.sourceUrl && !effectiveArchivedUrl && (
          <div className="mb-2.5"><span className="inline-flex items-center gap-1 rounded-lg border border-border bg-bg-2/40 px-2.5 py-1.5 font-mono text-[10px] text-faint">{item.recordId ?? "No public URL"}</span></div>
        )}

        <div className="flex items-center justify-end">
          <button type="button" onClick={copyCitation} className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/60 px-2.5 py-1.5 text-[11px] font-medium text-muted transition-colors duration-200 hover:border-accent/40 hover:text-accent" aria-label="Copy citation">
            {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
            {copied ? "Copied" : "Cite"}
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function MetaPill({ label, value, valueClassName = "text-text" }: { label: string; value: string; valueClassName?: string }) {
  return <div className="rounded-lg border border-border bg-bg-2/40 px-2.5 py-2"><div className="text-[9px] font-semibold uppercase tracking-wide text-faint">{label}</div><div className={`mt-1 truncate tabular text-[11.5px] font-semibold ${valueClassName}`}>{value}</div></div>;
}

function EvidenceChips({ icon, items, label, tone = "neutral" }: { icon: ReactNode; items?: string[]; label: string; tone?: "neutral" | "accent" }) {
  const shown = (items ?? []).filter(Boolean).slice(0, 4);
  if (shown.length === 0) return null;
  return (
    <div>
      <div className="mb-1 flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-faint">{icon}{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {shown.map((entry, index) => <span className={`rounded-md border px-2 py-0.5 text-[10px] ${tone === "accent" ? "border-accent/25 bg-accent/[0.08] text-accent" : "border-border bg-bg-2/60 text-muted"}`} key={`${label}-${entry}-${index}`}>{entry}</span>)}
      </div>
    </div>
  );
}
