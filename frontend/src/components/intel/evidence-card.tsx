"use client";

/**
 * EvidenceCard — the canonical provenance surface for SENTRY.
 *
 * Wherever the platform asserts a fact (an investigation finding, a dossier
 * claim, a report citation) the underlying evidence renders through this card so
 * provenance is never hidden. Every card exposes: source name, a clickable
 * source URL, "open original", publication date, a confidence read-out, and a
 * one-click "copy citation" that yields an analyst-grade reference string.
 *
 * Indian sources are visually promoted (India chip + copper edge); World Bank /
 * international feeds render as secondary.
 */

import { motion } from "framer-motion";
import {
  Check,
  Copy,
  ExternalLink,
  FileText,
  Globe2,
  ShieldCheck
} from "lucide-react";
import { useState } from "react";
import { isIndianSource, sourceMeta } from "@/lib/sources";

export type EvidenceItem = {
  /** Human title of the evidence (tender title, article headline, record label). */
  title: string;
  /** Raw source key or name — resolved through the source registry for labelling. */
  source: string;
  /** Canonical, clickable link to the original source, if any. */
  sourceUrl?: string | null;
  /** A stable record id (used when there is no URL). */
  recordId?: string | null;
  /** ISO date string of publication / award / capture. */
  date?: string | null;
  /** 0..1 confidence in the evidence. */
  confidence?: number | null;
  /** Optional one-line supporting detail. */
  detail?: string | null;
  /** Optional reference (tender ref, contract no.) shown mono. */
  reference?: string | null;
  /** Evidence class, drives the leading glyph. */
  kind?: "record" | "web" | "document";
};

function fmtDate(value?: string | null): string {
  if (!value) return "Undated";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

function buildCitation(e: EvidenceItem): string {
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 12) * 0.035, duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className={`group relative overflow-hidden rounded-[14px] border bg-surface/70 p-3.5 transition-colors hover:border-border-strong ${
        indian ? "border-l-2 border-l-accent/60 border-y-border border-r-border" : "border-border"
      }`}
    >
      {/* header: source identity */}
      <div className="flex items-center gap-2">
        <span
          className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${
            indian ? "border-accent/30 bg-accent/[0.08] text-accent" : "border-border bg-bg-2 text-muted"
          }`}
        >
          <Glyph className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-muted">{meta.label}</span>
        {indian && (
          <span className="shrink-0 rounded border border-accent/30 bg-accent/[0.08] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">
            India
          </span>
        )}
      </div>

      {/* body: title + detail */}
      <div className="mt-2">
        <div className="line-clamp-2 text-sm font-medium text-text">{item.title}</div>
        {item.detail && <div className="mt-1 line-clamp-2 text-xs text-muted">{item.detail}</div>}
        {item.reference && (
          <div className="mt-1 truncate font-mono text-[11px] text-faint">{item.reference}</div>
        )}
      </div>

      {/* meta row: date + confidence */}
      <div className="mt-2.5 flex items-center gap-3 text-[11px]">
        <span className="text-faint">{fmtDate(item.date)}</span>
        {conf && (
          <span className={`inline-flex items-center gap-1 ${conf.cls}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {Math.round((item.confidence as number) * 100)}%
          </span>
        )}
      </div>

      {/* action row: full provenance controls */}
      <div className="mt-3 flex items-center gap-1.5 border-t border-border/60 pt-2.5">
        {item.sourceUrl ? (
          <>
            <a
              href={item.sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/60 px-2 py-1 text-[11px] font-medium text-muted transition hover:border-accent/40 hover:text-accent"
            >
              <ExternalLink className="h-3 w-3" /> Open source
            </a>
            <a
              href={item.sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/60 px-2 py-1 text-[11px] font-medium text-muted transition hover:border-accent/40 hover:text-accent"
            >
              <FileText className="h-3 w-3" /> Document
            </a>
          </>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-2/40 px-2 py-1 font-mono text-[10px] text-faint">
            {item.recordId ?? "No public URL"}
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
    </motion.div>
  );
}
