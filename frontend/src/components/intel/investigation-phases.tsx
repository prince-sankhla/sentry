"use client";

import { Check, CircleDot, FileSearch, Flag, SearchCheck, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";

import { DURATION, EASE } from "@/lib/motion";

export type InvestigationPhaseKey = "intelligence" | "gaps" | "corroboration" | "assessment";

type Phase = {
  key: InvestigationPhaseKey;
  number: string;
  label: string;
  description: string;
  icon: typeof SearchCheck;
};

const PHASES: Phase[] = [
  {
    key: "intelligence",
    number: "01",
    label: "Intelligence",
    description: "Known records, entities, signals, relationships and source coverage.",
    icon: SearchCheck
  },
  {
    key: "gaps",
    number: "02",
    label: "Evidence gaps",
    description: "What is missing, weak or necessary to distinguish competing explanations.",
    icon: FileSearch
  },
  {
    key: "corroboration",
    number: "03",
    label: "Corroboration",
    description: "Test submitted or retrieved evidence against official records and known facts.",
    icon: ShieldCheck
  },
  {
    key: "assessment",
    number: "04",
    label: "Assessment",
    description: "Assemble the evidence-backed position, limitations and next review action.",
    icon: Flag
  }
];

export function InvestigationPhases({
  active = "intelligence",
  completed = []
}: {
  active?: InvestigationPhaseKey;
  completed?: InvestigationPhaseKey[];
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.base, ease: EASE }}
      aria-label="Investigation protocol"
      className="mt-5 overflow-hidden rounded-2xl border border-border bg-surface/70"
    >
      <div className="flex flex-col gap-2 border-b border-border bg-bg-2/40 px-5 py-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="t-label">Investigation protocol</div>
          <h2 className="mt-1 text-[16px] font-semibold tracking-[-0.02em] text-text">Follow the evidence through four phases</h2>
        </div>
        <div className="flex items-center gap-2 text-[10.5px] text-faint">
          <CircleDot className="h-3 w-3 text-accent" />
          One investigation record · one evidence trail
        </div>
      </div>

      <div className="grid md:grid-cols-4">
        {PHASES.map((phase, index) => {
          const Icon = phase.icon;
          const isActive = phase.key === active;
          const isComplete = completed.includes(phase.key);
          return (
            <div
              key={phase.key}
              className={`relative border-b border-border p-4 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0 ${isActive ? "bg-accent/[0.055]" : ""}`}
            >
              {index > 0 && <span className="absolute left-0 top-5 hidden h-8 w-px bg-border md:block" aria-hidden="true" />}
              <div className="flex items-start gap-3">
                <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border ${isActive ? "border-accent/30 bg-accent/[0.08] text-accent" : "border-border bg-bg-2 text-muted"}`}>
                  {isComplete ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[9px] tracking-[0.16em] text-faint">{phase.number}</span>
                    <span className="text-[12.5px] font-semibold text-text">{phase.label}</span>
                    {isActive && <span className="rounded-full bg-accent/10 px-1.5 py-0.5 text-[8.5px] font-semibold uppercase tracking-wide text-accent">Current</span>}
                  </div>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-faint">{phase.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-border px-5 py-3 text-[10.5px] leading-relaxed text-faint">
        SENTRY treats screening signals as review leads. A signal is not a finding of misconduct, and incomplete evidence is not treated as proof.
      </div>
    </motion.section>
  );
}
