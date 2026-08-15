"use client";

/**
 * AiMemory — cross-investigation continuity.
 *
 * When the backend recalls related prior investigations from memory
 * (`prior_investigations`), this surfaces them: the subject, prior risk verdict,
 * when it was assessed, its confidence, and why it matched. The analyst can reuse
 * a prior investigation (re-run it) to compare findings over time.
 */

import { motion } from "framer-motion";
import { ArrowUpRight, Brain, History, Repeat } from "lucide-react";
import type { MemoryHit } from "@/lib/api";
import { DURATION, EASE } from "@/lib/motion";

const RISK_CLS: Record<string, string> = {
  critical: "border-risk-crit/60 bg-risk-crit/15 text-risk-crit",
  high: "border-risk-high/40 bg-risk-high/10 text-risk-high",
  medium: "border-risk-med/40 bg-risk-med/10 text-risk-med",
  low: "border-risk-low/40 bg-risk-low/10 text-risk-low",
  insufficient: "border-border bg-surface-2 text-muted"
};

function fmtDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat("en", { day: "2-digit", month: "short", year: "numeric" }).format(d);
}

export function AiMemory({ hits, onReuse }: { hits: MemoryHit[]; onReuse: (query: string) => void }) {
  if (hits.length === 0) return null;
  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-1.5 text-[11px] text-faint">
        <Brain className="h-3.5 w-3.5 text-accent" /> Recalled from cross-investigation memory
      </div>
      {hits.map((hit, i) => (
        <motion.div
          key={`${hit.subject}-${i}`}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.06, duration: DURATION.base, ease: EASE }}
          className="rounded-xl border border-border bg-surface/60 p-4 transition-colors duration-200 hover:border-border-strong"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-[13.5px] font-semibold text-text">{hit.subject}</div>
              <div className="mt-1 flex items-center gap-1.5 text-[11px] text-faint">
                <History className="h-3 w-3" /> {fmtDate(hit.remembered_at)} · {hit.investigation_type}
              </div>
            </div>
            <span
              className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                RISK_CLS[hit.risk_level] ?? RISK_CLS.insufficient
              }`}
            >
              {hit.risk_level}
            </span>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-muted">
            <span className="inline-flex items-center gap-1">
              Records reviewed <span className="ml-1 tabular font-semibold text-text">{hit.records_reviewed}</span>
            </span>
            <span className="truncate text-faint">{hit.match_reason}</span>
          </div>

          {hit.key_indicators.length > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {hit.key_indicators.slice(0, 4).map((k, j) => (
                <span key={j} className="rounded-md border border-border bg-bg-2/50 px-2 py-0.5 text-[10px] text-muted">
                  {k}
                </span>
              ))}
            </div>
          )}

          <div className="mt-3.5 flex items-center gap-2 border-t border-border/60 pt-3">
            <button
              type="button"
              onClick={() => onReuse(hit.subject)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/[0.08] px-2.5 py-1.5 text-[11px] font-medium text-accent transition-colors duration-200 hover:bg-accent/15"
            >
              <Repeat className="h-3 w-3" /> Reuse investigation
            </button>
            <button
              type="button"
              onClick={() => onReuse(hit.subject)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/60 px-2.5 py-1.5 text-[11px] font-medium text-muted transition-colors duration-200 hover:border-accent/40 hover:text-accent"
            >
              <ArrowUpRight className="h-3 w-3" /> Compare
            </button>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
