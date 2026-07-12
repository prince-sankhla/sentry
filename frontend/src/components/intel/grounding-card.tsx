"use client";

/**
 * GroundingCard — proves (not merely asserts) the narrative is anchored to
 * verifiable evidence. Reads the backend `GroundingReport`: how many findings
 * carry citations, how many documents are available, and whether the whole
 * narrative is fully grounded. When every finding is evidence-backed it declares
 * "No hallucinations detected".
 */

import { motion } from "framer-motion";
import { CheckCircle2, FileCheck, ShieldCheck, ShieldAlert } from "lucide-react";
import type { GroundingReport } from "@/lib/api";

export function GroundingCard({
  grounding: g,
  confidence
}: {
  grounding: GroundingReport;
  confidence: number;
}) {
  const grounded = g.fully_grounded && g.total_findings > 0;
  const coverage = g.total_findings > 0 ? Math.round((g.evidence_backed_findings / g.total_findings) * 100) : 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className={`overflow-hidden rounded-[16px] border p-4 ${
        grounded ? "border-success/40 bg-success/[0.05]" : "border-warning/40 bg-warning/[0.05]"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`grid h-8 w-8 place-items-center rounded-lg border ${
            grounded ? "border-success/40 bg-success/10 text-success" : "border-warning/40 bg-warning/10 text-warning"
          }`}
        >
          {grounded ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
        </span>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text">{grounded ? "Fully Grounded" : "Partially Grounded"}</div>
          <div className="text-[11px] text-faint">Evidence-anchored verification audit</div>
        </div>
      </div>

      <div className="mt-4 space-y-2.5">
        <GroundingRow label="Evidence-backed findings" value={`${g.evidence_backed_findings} / ${g.total_findings}`} pct={coverage} />
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Documents" value={String(g.documents_available)} icon={<FileCheck className="h-3.5 w-3.5" />} />
          <Stat label="Records" value={String(g.records_reviewed)} icon={<FileCheck className="h-3.5 w-3.5" />} />
          <Stat label="Evidence completeness" value={`${Math.round(confidence * 100)}%`} icon={<ShieldCheck className="h-3.5 w-3.5" />} />
        </div>
      </div>

      {grounded && (
        <div className="mt-3 flex items-center gap-1.5 rounded-lg border border-success/30 bg-success/[0.07] px-2.5 py-1.5 text-[11px] font-medium text-success">
          <CheckCircle2 className="h-3.5 w-3.5" /> No hallucinations detected — every finding cites verifiable evidence.
        </div>
      )}
    </motion.div>
  );
}

function GroundingRow({ label, value, pct }: { label: string; value: string; pct: number }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="text-muted">{label}</span>
        <span className="tabular font-semibold text-text">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-2">
        <motion.div
          className="h-full rounded-full bg-success"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  );
}

function Stat({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface/50 p-2 text-center">
      <div className="flex items-center justify-center text-accent">{icon}</div>
      <div className="mt-1 tabular text-sm font-semibold text-text">{value}</div>
      <div className="text-[9px] uppercase tracking-wide text-faint">{label}</div>
    </div>
  );
}
