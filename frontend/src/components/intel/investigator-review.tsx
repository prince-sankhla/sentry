"use client";

/**
 * INVESTIGATOR REVIEW — the core reasoning section of every investigation.
 *
 * SENTRY organizes evidence; it does not decide guilt. This section presents
 * exactly three evidence-driven columns, mirroring how a senior procurement
 * investigator thinks:
 *
 *   1. Evidence Supporting Investigation      — objective facts only
 *   2. Evidence Supporting Routine Procurement — competing evidence (never
 *      cancels the finding, never speculated)
 *   3. Evidence Still Required                — what would distinguish routine
 *      from suspicious procurement
 *
 * Everything shown is deterministic and traceable to its source (`basis` +
 * supporting tender references). No probabilities, no confidence meters,
 * no verdicts.
 */
import { motion } from "framer-motion";
import { CircleHelp, Scale, ShieldQuestion, Search } from "lucide-react";

import { Section } from "@/components/ui/card";
import type { InvestigatorReview as InvestigatorReviewData, InvestigatorReviewItem } from "@/lib/api";
import { DURATION, EASE } from "@/lib/motion";

const COLUMNS = [
  {
    key: "supporting" as const,
    title: "Evidence Supporting Investigation",
    hint: "Objective facts that increase investigative interest.",
    icon: Search,
    accent: "border-warning/40 text-warning",
    dot: "bg-warning"
  },
  {
    key: "routine" as const,
    title: "Evidence Supporting Routine Procurement",
    hint: "Competing evidence. It does not cancel the finding — it sits beside it.",
    icon: Scale,
    accent: "border-success/40 text-success",
    dot: "bg-success"
  },
  {
    key: "required" as const,
    title: "Evidence Still Required",
    hint: "What would distinguish routine from suspicious procurement.",
    icon: CircleHelp,
    accent: "border-accent/40 text-accent",
    dot: "bg-accent"
  }
];

export function InvestigatorReview({
  review,
  caseFacts = false
}: {
  review: InvestigatorReviewData;
  /**
   * Case-facts mode: show only the case-level supporting/routine columns.
   * Finding-level items and the evidence-still-required list live in each
   * finding's case file — referenced there, never duplicated here.
   */
  caseFacts?: boolean;
}) {
  const columns = caseFacts ? COLUMNS.filter((c) => c.key !== "required") : COLUMNS;
  if (caseFacts && review.supporting.length === 0 && review.routine.length === 0) return null;
  return (
    <Section
      eyebrow="Evidence review"
      title={caseFacts ? "Case-level facts" : "What the evidence says — and what it doesn't yet"}
      action={
        <span className="inline-flex items-center gap-1.5 text-xs text-faint">
          <ShieldQuestion className="h-3.5 w-3.5" />
          Evidence organized, not judged
        </span>
      }
    >
      <div className={`grid grid-cols-1 gap-3 ${caseFacts ? "lg:grid-cols-2" : "lg:grid-cols-3"}`}>
        {columns.map((col, c) => {
          const items = review[col.key];
          const Icon = col.icon;
          return (
            <motion.div
              key={col.key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: c * 0.06, duration: DURATION.base, ease: EASE }}
              className={`flex flex-col rounded-xl border bg-bg-2/40 ${col.accent.split(" ")[0]}`}
            >
              <div className="border-b border-border/60 p-4">
                <div className={`flex items-center gap-2 text-[13.5px] font-semibold ${col.accent.split(" ")[1]}`}>
                  <Icon className="h-4 w-4" />
                  {col.title}
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-faint">{col.hint}</p>
              </div>
              <ul className="flex-1 space-y-2.5 p-4">
                {items.length === 0 ? (
                  <li className="text-xs text-faint">
                    {col.key === "routine"
                      ? "No competing contextual evidence detected in the retrieved records."
                      : "None identified from the retrieved records."}
                  </li>
                ) : (
                  items.map((item, i) => <ReviewLine key={i} item={item} dot={col.dot} />)
                )}
              </ul>
            </motion.div>
          );
        })}
      </div>
      <p className="mt-3 text-[11px] leading-snug text-faint">{review.principle}</p>
    </Section>
  );
}

function ReviewLine({ item, dot }: { item: InvestigatorReviewItem; dot: string }) {
  return (
    <li className="flex items-start gap-2.5">
      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
      <span className="min-w-0">
        <span className="block text-[13px] leading-relaxed text-text">{item.statement}</span>
        <span className="mt-0.5 block truncate font-mono text-[10px] text-faint">
          {item.basis}
          {item.records.length > 0 ? ` · ${item.records.length} record${item.records.length === 1 ? "" : "s"}` : ""}
        </span>
      </span>
    </li>
  );
}
