"use client";

import { motion } from "framer-motion";
import { ArrowRight, Boxes, FileCheck2, GitBranch, Landmark, ScanSearch, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Section 4 — "How SENTRY works". A horizontal pipeline of the six real stages
 * of the platform; each stage animates in on scroll. Mirrors the backend flow
 * (connectors → normalization → entity resolution → graph → evidence → workspace).
 */

const STAGES: { icon: LucideIcon; label: string; detail: string }[] = [
  { icon: Landmark, label: "Official Sources", detail: "Government portals & registries" },
  { icon: Boxes, label: "Normalization", detail: "One schema, full provenance" },
  { icon: ScanSearch, label: "Entity Resolution", detail: "Buyers, suppliers, directors" },
  { icon: GitBranch, label: "Knowledge Graph", detail: "Records linked into evidence" },
  { icon: ShieldCheck, label: "Evidence Engine", detail: "Deterministic indicators" },
  { icon: FileCheck2, label: "Investigation Workspace", detail: "Findings, review, export" }
];

export function SectionPipeline() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          How SENTRY works
        </div>
        <h2 className="text-4xl font-semibold tracking-tight text-text sm:text-5xl">
          From raw data to a working investigation
        </h2>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          return (
            <div key={stage.label} className="flex flex-1 items-center gap-4 lg:flex-col lg:gap-0">
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.55, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                className="mkt-glass group flex w-full flex-1 flex-col items-center rounded-2xl p-5 text-center transition-colors hover:border-accent/30"
              >
                <span className="grid h-12 w-12 place-items-center rounded-xl border border-accent/25 bg-accent/[0.08] text-accent">
                  <Icon className="h-5 w-5" />
                </span>
                <div className="mt-3 text-sm font-semibold text-text">{stage.label}</div>
                <div className="mt-1 text-xs leading-snug text-muted">{stage.detail}</div>
                <span className="mt-3 text-[10px] font-semibold tracking-widest text-faint">
                  0{i + 1}
                </span>
              </motion.div>

              {i < STAGES.length - 1 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 + 0.25 }}
                  className="shrink-0 text-border-strong lg:my-2 lg:rotate-90"
                >
                  <ArrowRight className="h-4 w-4" />
                </motion.div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
