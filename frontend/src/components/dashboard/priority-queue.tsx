"use client";

/**
 * Priority Investigation Queue.
 *
 * A professional investigator's starting point. Buyer-level leads are ranked
 * from the deterministic investigation engine, while explicit field-ready and
 * CAG records are surfaced as direct tender leads so they can be opened from
 * the same Investigation Workspace.
 */
import { motion } from "framer-motion";
import { ArrowRight, Check, FileText, Layers, ListChecks, ShieldQuestion } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Section } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { getPriorityQueue, type PriorityQueueItem } from "@/lib/api";

const PRIORITY_STYLE: Record<PriorityQueueItem["priority"], { label: string; cls: string; dot: string }> = {
  critical: { label: "Critical", cls: "border-danger/50 bg-danger/10 text-danger", dot: "bg-danger" },
  high: { label: "High", cls: "border-danger/40 bg-danger/10 text-danger", dot: "bg-danger" },
  medium: { label: "Medium", cls: "border-warning/40 bg-warning/10 text-warning", dot: "bg-warning" },
  review: { label: "Review", cls: "border-border bg-surface text-muted", dot: "bg-border-strong" }
};

const EVIDENCE_STYLE: Record<PriorityQueueItem["evidence_strength"], string> = {
  high: "text-success",
  moderate: "text-warning",
  limited: "text-muted"
};

function patternLabel(item: PriorityQueueItem): string {
  return item.primary_pattern?.trim() || "Deterministic indicators triggered";
}

export function PriorityInvestigationQueue({ onOpen }: { onOpen: (subject: string) => void }) {
  const [items, setItems] = useState<PriorityQueueItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    // The queue now includes explicit direct-tender leads in addition to the
    // established buyer-risk leads, so request enough room to show both.
    getPriorityQueue(20)
      .then((res) => alive && setItems(res.items))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  if (failed) return null;

  return (
    <Section
      eyebrow="Where to start today"
      title="Priority Investigation Queue"
      action={
        <span className="inline-flex items-center gap-1.5 text-xs text-faint">
          <ListChecks className="h-3.5 w-3.5" />
          Ranked from the current procurement database
        </span>
      }
    >
      {items === null ? (
        <QueueSkeleton />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<ShieldQuestion className="h-5 w-5" />}
          title="No investigations queued"
          message="Risk-ranked buyer leads and explicit field-ready tender records will surface here when available."
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {items.map((item, i) => (
            <QueueCard key={`${item.subject}-${item.investigation_type}-${i}`} item={item} index={i} onOpen={onOpen} />
          ))}
        </div>
      )}
    </Section>
  );
}

function QueueCard({
  item,
  index,
  onOpen
}: {
  item: PriorityQueueItem;
  index: number;
  onOpen: (subject: string) => void;
}) {
  const style = PRIORITY_STYLE[item.priority];
  const open = useCallback(() => onOpen(item.subject), [item.subject, onOpen]);
  const isTender = item.investigation_type === "tender";
  const subjectLabel = isTender ? "Tender lead" : "Entity";

  return (
    <motion.button
      type="button"
      onClick={open}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.04, duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="group flex flex-col gap-3 rounded-2xl border border-border bg-bg-2/40 p-4 text-left transition hover:border-accent/40 hover:bg-bg-2/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
    >
      <div className="flex items-center justify-between gap-2">
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${style.cls}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
          {style.label}
        </span>
        <span className="text-[11px] text-faint">
          Evidence{" "}
          <span className={`font-semibold ${EVIDENCE_STYLE[item.evidence_strength]}`}>{item.evidence_strength}</span>
        </span>
      </div>

      <div className="min-w-0">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{subjectLabel}</div>
        <div className="mt-0.5 line-clamp-2 text-[15px] font-semibold text-text group-hover:text-accent">{item.subject}</div>
      </div>

      <div className="min-w-0">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Potential pattern</div>
        <div className="mt-0.5 truncate text-sm text-muted">{patternLabel(item)}</div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
        <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-1.5 py-0.5 text-muted">
          <Layers className="h-3 w-3" /> {item.typology_count} typolog{item.typology_count === 1 ? "y" : "ies"}
        </span>
        <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-1.5 py-0.5 text-muted">
          <FileText className="h-3 w-3" /> {item.linked_records} linked record{item.linked_records === 1 ? "" : "s"}
        </span>
      </div>

      <div className="rounded-lg border border-border bg-surface/50 px-2.5 py-2">
        <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-faint">Why this is recommended</div>
        <ul className="mt-1 space-y-1">
          {item.reasons.map((reason, r) => (
            <li key={r} className="flex items-start gap-1.5 text-[11px] leading-snug text-muted">
              <Check className="mt-0.5 h-3 w-3 shrink-0 text-accent" />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-auto flex items-center justify-end gap-2 border-t border-border/60 pt-2.5">
        <span className="inline-flex shrink-0 items-center gap-1 text-[12px] font-semibold text-accent">
          Open investigation
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </motion.button>
  );
}

function QueueSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-[168px] animate-pulse rounded-2xl border border-border bg-bg-2/40" />
      ))}
    </div>
  );
}
