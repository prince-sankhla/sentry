"use client";

import { motion } from "framer-motion";
import {
  FileSpreadsheet,
  FileText,
  GitBranch,
  Globe2,
  Clock,
  Layers,
  Mail,
  Search,
  Sparkles,
  Unlink,
  Workflow
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Section 3 — Traditional investigation vs SENTRY. Two glass panels; rows
 * stagger in from opposite sides as the section enters the viewport.
 */

const TRADITIONAL: { icon: LucideIcon; label: string }[] = [
  { icon: FileSpreadsheet, label: "Excel sheets" },
  { icon: FileText, label: "PDFs" },
  { icon: Mail, label: "Emails" },
  { icon: Globe2, label: "Government portals" },
  { icon: Search, label: "Manual research" },
  { icon: Unlink, label: "Disconnected information" }
];

const SENTRY: { icon: LucideIcon; label: string }[] = [
  { icon: Layers, label: "One investigation workspace" },
  { icon: Workflow, label: "Connected evidence" },
  { icon: GitBranch, label: "Knowledge graph" },
  { icon: Clock, label: "Timeline" },
  { icon: Sparkles, label: "AI assistance" }
];

function Panel({
  title,
  items,
  accent,
  fromX
}: {
  title: string;
  items: { icon: LucideIcon; label: string }[];
  accent: boolean;
  fromX: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: fromX }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={`mkt-glass mkt-glass-hi rounded-2xl p-6 ${
        accent ? "border-accent/30" : ""
      }`}
    >
      <div
        className={`text-[11px] font-semibold uppercase tracking-[0.18em] ${
          accent ? "text-accent" : "text-faint"
        }`}
      >
        {title}
      </div>
      <ul className="mt-5 space-y-2.5">
        {items.map(({ icon: Icon, label }, i) => (
          <motion.li
            key={label}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.15 + i * 0.07, duration: 0.45 }}
            className={`flex items-center gap-3 rounded-xl border px-3.5 py-2.5 text-sm ${
              accent
                ? "border-accent/20 bg-accent/[0.05] text-text"
                : "border-border bg-bg-2/60 text-muted"
            }`}
          >
            <Icon className={`h-4 w-4 shrink-0 ${accent ? "text-accent" : "text-faint"}`} />
            {label}
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
}

export function SectionComparison() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="mx-auto mb-14 max-w-2xl text-center">
        <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          The difference
        </div>
        <h2 className="text-4xl font-semibold tracking-tight text-text sm:text-5xl">
          From scattered files to one workspace
        </h2>
      </div>

      <div className="relative grid grid-cols-1 gap-6 md:grid-cols-2">
        <Panel title="Traditional investigation" items={TRADITIONAL} accent={false} fromX={-24} />
        <Panel title="SENTRY" items={SENTRY} accent fromX={24} />

        {/* center vs marker (desktop) */}
        <div className="pointer-events-none absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 md:block">
          <div className="grid h-12 w-12 place-items-center rounded-full border border-border-strong bg-bg text-xs font-bold text-muted">
            VS
          </div>
        </div>
      </div>
    </section>
  );
}
