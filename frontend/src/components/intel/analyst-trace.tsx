"use client";

/**
 * AnalystTrace — the auditable, tool-driven reasoning path.
 *
 * Renders the backend `analyst_trace`: each step names the read-only tool it ran
 * over the InvestigationPackage, the grounded observation it produced, and the
 * evidence backing it. Every step expands to reveal its citations, so the
 * analyst can walk the exact reasoning chain and verify each observation.
 */

import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronRight, ExternalLink, Wrench } from "lucide-react";
import { useState } from "react";
import type { AnalystStep, ReasoningCitation } from "@/lib/api";
import { sourceMeta } from "@/lib/sources";

/** Human-format a snake/camel tool identifier into a readable step name. */
function toolLabel(tool: string): string {
  return tool
    .replace(/[_\-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AnalystTrace({ steps }: { steps: AnalystStep[] }) {
  if (steps.length === 0) return null;
  return (
    <div className="relative">
      {/* spine */}
      <span className="absolute bottom-4 left-[15px] top-4 w-px bg-border" aria-hidden />
      <ol className="space-y-1">
        {steps.map((step, i) => (
          <TraceStep key={step.order} step={step} index={i} />
        ))}
      </ol>
    </div>
  );
}

function TraceStep({ step, index }: { step: AnalystStep; index: number }) {
  const [open, setOpen] = useState(false);
  const count = step.citations.length;

  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="relative flex items-start gap-3 py-1.5"
    >
      {/* node */}
      <motion.span
        initial={{ scale: 0.4, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: index * 0.08 + 0.1, type: "spring", stiffness: 340, damping: 20 }}
        className="relative z-10 mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full border-2 border-success/50 bg-success/10 text-success"
      >
        <Check className="h-3.5 w-3.5" />
      </motion.span>

      {/* body */}
      <div className="min-w-0 flex-1 rounded-[14px] border border-border bg-surface/60 p-3 transition hover:border-border-strong">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Wrench className="h-3 w-3 shrink-0 text-accent" />
              <span className="truncate text-sm font-semibold text-text">{toolLabel(step.tool)}</span>
            </div>
            {step.input && <div className="mt-0.5 truncate font-mono text-[10px] text-faint">{step.input}</div>}
          </div>
          <span className="shrink-0 rounded-full border border-border bg-bg-2/60 px-2 py-0.5 text-[10px] font-medium text-muted">
            {count} evidence
          </span>
        </div>

        <p className="mt-2 text-[13px] leading-relaxed text-muted">{step.observation}</p>

        {count > 0 && (
          <>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="mt-2.5 inline-flex items-center gap-1.5 text-[11px] font-medium text-accent transition hover:text-accent-hi"
            >
              <ChevronRight className={`h-3.5 w-3.5 transition ${open ? "rotate-90" : ""}`} />
              {open ? "Hide" : "Show"} citations
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
                  <ul className="mt-2 space-y-1.5">
                    {step.citations.map((c, i) => (
                      <TraceCitation key={i} citation={c} />
                    ))}
                  </ul>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </motion.li>
  );
}

function TraceCitation({ citation }: { citation: ReasoningCitation }) {
  const meta = sourceMeta(citation.source_name);
  const href = citation.source_url ?? citation.document_url;
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg border border-border bg-bg-2/50 px-2.5 py-1.5">
      <span className="min-w-0">
        <span className="block truncate text-[11px] text-text">{citation.label}</span>
        <span className="block truncate text-[10px] text-faint">
          {meta.short}
          {citation.related_tender ? ` · ${citation.related_tender}` : ""}
        </span>
      </span>
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="inline-flex shrink-0 items-center gap-1 text-[10px] text-accent hover:underline"
        >
          Verify <ExternalLink className="h-3 w-3" />
        </a>
      ) : (
        <span className="shrink-0 font-mono text-[10px] text-faint">{citation.source_record_id ?? "—"}</span>
      )}
    </li>
  );
}
