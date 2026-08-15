"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Award, CalendarClock, ChevronDown, ExternalLink, FileText, Flag } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { TimelineEvent } from "@/lib/api";
import { DURATION, EASE } from "@/lib/motion";
import { formatDate } from "@/lib/format";

const KIND = {
  tender_published: { icon: FileText, tone: "text-info border-info/40 bg-info/10", dot: "bg-info", label: "Tender published" },
  tender_closing: { icon: Flag, tone: "text-risk-med border-risk-med/40 bg-risk-med/10", dot: "bg-risk-med", label: "Tender closing" },
  award: { icon: Award, tone: "text-success border-success/40 bg-success/10", dot: "bg-success", label: "Award" }
} as const;

function hrefFor(e: TimelineEvent): string | null {
  if (e.entity_type === "tender" && e.entity_id) return `/tenders/${e.entity_id}`;
  if (e.entity_type === "company" && e.entity_id) return `/companies/${e.entity_id}`;
  return null;
}

function TimelineEventCard({ event: e, index }: { event: TimelineEvent; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const meta = KIND[e.kind] ?? KIND.tender_published;
  const Icon = meta.icon;
  const href = hrefFor(e);
  const hasDetail = Boolean(e.subtitle || href);

  const cardContent = (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index, 20) * 0.025, duration: DURATION.base, ease: EASE }}
      className={`relative rounded-xl border border-border bg-surface p-4 transition-colors duration-200 ${
        hasDetail ? "cursor-pointer hover:border-border-strong hover:bg-surface/80" : ""
      }`}
      onClick={hasDetail ? () => setExpanded((v) => !v) : undefined}
    >
      {/* timeline connector dot */}
      <span
        className={`absolute -left-[30px] top-4 grid h-6 w-6 place-items-center rounded-full border ${meta.tone}`}
      >
        <Icon className="h-3 w-3" />
      </span>

      {/* header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">
            {meta.label}
          </span>
          {e.reference && (
            <>
              <span className="text-faint">·</span>
              <span className="font-mono text-[11px] text-faint">{e.reference}</span>
            </>
          )}
        </div>
        {hasDetail && (
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-muted transition-transform duration-200 ${
              expanded ? "rotate-180" : ""
            }`}
          />
        )}
      </div>

      {/* title */}
      <div className="mt-1.5 text-[13.5px] font-medium leading-snug text-text">{e.title}</div>

      {/* expandable detail */}
      <AnimatePresence initial={false}>
        {expanded && hasDetail && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: DURATION.fast, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="mt-3 border-t border-border/60 pt-3">
              {e.subtitle && (
                <p className="text-[12.5px] leading-relaxed text-muted">{e.subtitle}</p>
              )}
              {href && (
                <Link
                  href={href}
                  onClick={(ev) => ev.stopPropagation()}
                  className="mt-2.5 inline-flex items-center gap-1.5 text-[12px] font-medium text-accent hover:underline"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  {e.entity_type === "tender" ? "View tender detail" : "View company profile"}
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );

  return href && !hasDetail ? (
    <Link href={href} className="block">
      {cardContent}
    </Link>
  ) : (
    cardContent
  );
}

export function TimelineView({ groups }: { groups: [string, TimelineEvent[]][] }) {
  let globalIndex = 0;

  return (
    <div className="space-y-10">
      {groups.map(([day, events]) => (
        <motion.div
          key={day}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: DURATION.base, ease: EASE }}
        >
          {/* sticky date header */}
          <div className="sticky top-16 z-10 mb-4 flex items-center gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-bg-2/90 px-3 py-1 text-xs font-medium text-muted backdrop-blur">
              <CalendarClock className="h-3.5 w-3.5 text-accent" />
              {formatDate(day)}
            </div>
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border bg-bg-2 text-[10px] font-semibold text-faint">
              {events.length}
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* event rows */}
          <div className="ml-1 space-y-2.5 border-l border-border pl-6">
            {events.map((e) => {
              const i = globalIndex++;
              return <TimelineEventCard key={`${e.entity_id}-${i}`} event={e} index={i} />;
            })}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
