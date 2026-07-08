"use client";

/**
 * AiInvestigationPanel — the command surface for an AI investigation.
 *
 * Replaces the old static "AI section". Surfaces, in one Gotham-grade panel,
 * every top-level reasoning signal the backend already produces: the executive
 * summary, the analyst's risk reasoning, overall confidence, grounding status,
 * evidence coverage, the provider that answered, processing time and evidence
 * count. Nothing here is fabricated — every value is read from the grounded
 * `InvestigationReasoning` payload (plus the client-measured elapsed time).
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Clock,
  Database,
  Gauge,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Timer
} from "lucide-react";
import type { InvestigationReasoning, InvestigationRiskLevel } from "@/lib/api";
import { ProviderBadge, providerDisplayName } from "@/components/intel/provider-badge";

const RISK: Record<InvestigationRiskLevel, { label: string; text: string; ring: string; bar: string }> = {
  critical: { label: "Critical Risk", text: "text-danger", ring: "border-danger/50 bg-danger/[0.07]", bar: "bg-danger" },
  high: { label: "High Risk", text: "text-danger", ring: "border-danger/40 bg-danger/[0.05]", bar: "bg-danger" },
  medium: { label: "Medium Risk", text: "text-warning", ring: "border-warning/40 bg-warning/[0.05]", bar: "bg-warning" },
  low: { label: "Low Risk", text: "text-success", ring: "border-success/40 bg-success/[0.05]", bar: "bg-success" },
  insufficient: { label: "Insufficient Evidence", text: "text-muted", ring: "border-border bg-surface", bar: "bg-border-strong" }
};

function fmtElapsed(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function AiInvestigationPanel({
  reasoning,
  processingMs
}: {
  reasoning: InvestigationReasoning;
  processingMs: number | null;
}) {
  const style = RISK[reasoning.risk_level];
  const insufficient = reasoning.insufficient_evidence || reasoning.risk_level === "insufficient";
  const g = reasoning.grounding;
  const coverage = g.total_findings > 0 ? g.evidence_backed_findings / g.total_findings : 1;
  const confidencePct = Math.round(reasoning.confidence * 100);
  const grounded = g.fully_grounded && g.total_findings > 0;

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className={`relative overflow-hidden rounded-[20px] border ${style.ring} elevate`}
    >
      {/* copper dawn wash */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-accent/[0.06] blur-3xl"
      />

      {/* header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-bg-2/40 px-5 py-3.5">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          <Sparkles className="h-3.5 w-3.5" /> AI Investigation
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${style.ring} ${style.text}`}
          >
            {insufficient ? (
              <ShieldAlert className="h-3.5 w-3.5" />
            ) : reasoning.risk_level === "low" ? (
              <ShieldCheck className="h-3.5 w-3.5" />
            ) : (
              <ShieldAlert className="h-3.5 w-3.5" />
            )}
            {style.label}
          </span>
          <ProviderBadge generatedBy={reasoning.generated_by} provider={reasoning.provider} model={reasoning.model} />
        </div>
      </div>

      <div className="grid gap-5 p-5 lg:grid-cols-[1fr_300px]">
        {/* left — summary + reasoning */}
        <div className="min-w-0">
          <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Executive summary</div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="max-w-3xl text-[15px] leading-relaxed text-text"
          >
            {reasoning.executive_summary}
          </motion.p>

          {reasoning.risk_rationale.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">
                <Activity className="h-3 w-3 text-accent" /> Analyst reasoning
              </div>
              <div className="flex flex-wrap gap-1.5">
                <AnimatePresence>
                  {reasoning.risk_rationale.map((r, i) => (
                    <motion.span
                      key={r}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.15 + i * 0.05 }}
                      className="rounded-md border border-border bg-surface/70 px-2.5 py-1 text-[11px] text-muted"
                    >
                      {r}
                    </motion.span>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center gap-2 border-t border-border/50 pt-3 text-[11px] text-faint">
            {reasoning.generated_by === "llm" ? (
              <>
                <Sparkles className="h-3 w-3 text-accent" />
                Reasoning authored by {providerDisplayName(reasoning.provider, reasoning.model)}, grounded strictly in the
                cited evidence.
              </>
            ) : (
              <>
                <Activity className="h-3 w-3 text-accent" />
                Deterministic reasoning composed directly from procurement evidence — no external model was used.
              </>
            )}
          </div>
        </div>

        {/* right — metrics rail */}
        <div className="flex flex-col gap-3">
          {/* confidence meter */}
          <div className="rounded-[14px] border border-border bg-surface/60 p-3.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
                <Gauge className="h-3 w-3" /> Investigation confidence
              </span>
              <span className={`tabular text-sm font-semibold ${style.text}`}>{confidencePct}%</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-bg-2">
              <motion.div
                className={`h-full rounded-full ${style.bar}`}
                initial={{ width: 0 }}
                animate={{ width: `${confidencePct}%` }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
          </div>

          {/* grounding + coverage */}
          <div className="grid grid-cols-2 gap-3">
            <MetricTile
              icon={grounded ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
              label="Grounding"
              value={grounded ? "Fully grounded" : insufficient ? "Insufficient" : "Partial"}
              tone={grounded ? "success" : insufficient ? "muted" : "warning"}
            />
            <MetricTile
              icon={<Database className="h-3.5 w-3.5" />}
              label="Evidence coverage"
              value={`${g.evidence_backed_findings}/${g.total_findings || 0}`}
              tone={coverage >= 1 ? "success" : coverage > 0 ? "warning" : "muted"}
            />
            <MetricTile
              icon={<Timer className="h-3.5 w-3.5" />}
              label="Processing time"
              value={fmtElapsed(processingMs)}
              tone="accent"
            />
            <MetricTile
              icon={<Clock className="h-3.5 w-3.5" />}
              label="Evidence count"
              value={String(reasoning.evidence_ledger.length)}
              tone="accent"
            />
          </div>
        </div>
      </div>
    </motion.section>
  );
}

const TILE_TONE = {
  accent: "text-accent",
  success: "text-success",
  warning: "text-warning",
  muted: "text-muted"
} as const;

function MetricTile({
  icon,
  label,
  value,
  tone
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: keyof typeof TILE_TONE;
}) {
  return (
    <div className="rounded-[12px] border border-border bg-surface/60 p-2.5">
      <div className={`flex items-center gap-1.5 ${TILE_TONE[tone]}`}>
        {icon}
        <span className="text-[9px] font-semibold uppercase tracking-[0.12em] text-faint">{label}</span>
      </div>
      <div className={`mt-1.5 truncate text-sm font-semibold ${TILE_TONE[tone]}`}>{value}</div>
    </div>
  );
}
