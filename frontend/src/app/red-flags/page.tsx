"use client";

import { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  FileSearch,
  GitBranch,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles
} from "lucide-react";

import {
  streamInvestigation,
  type InvestigationReport,
  type RiskAssessmentV2,
  type RiskIndicatorV2,
  type RiskPattern
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageShell } from "@/components/ui/page";
import { Section } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { EmptyState, ErrorState } from "@/components/ui/states";

const SEVERITY_RANK = { low: 1, medium: 2, high: 3, critical: 4, insufficient: 0 } as const;

function severityTone(severity: string) {
  if (severity === "critical") return "border-danger/40 bg-danger/10 text-danger";
  if (severity === "high") return "border-warning/40 bg-warning/10 text-warning";
  if (severity === "medium") return "border-accent/30 bg-accent/10 text-accent";
  return "border-border bg-bg-2/40 text-faint";
}

function evidenceTone(status: string) {
  if (status === "verified") return "success" as const;
  if (status === "probable") return "accent" as const;
  return "neutral" as const;
}

export default function RedFlagsPage() {
  const [query, setQuery] = useState("");
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  const risk = report?.package.risk_assessment_v2 ?? null;
  const rankedIndicators = useMemo(() => {
    return [...(risk?.indicators ?? [])].sort(
      (a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity] || b.score - a.score
    );
  }, [risk]);
  const patterns = risk?.patterns ?? [];

  const investigate = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed || running) return;
    setRunning(true);
    setError(null);
    setReport(null);
    setOpenId(null);

    streamInvestigation(trimmed, {
      onReport: (next) => {
        setReport(next);
        setRunning(false);
      },
      onError: (message) => {
        setError(message);
        setRunning(false);
      }
    });
  }, [query, running]);

  return (
    <PageShell>
      <div className="mx-auto max-w-7xl pb-16 pt-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
            <ShieldCheck className="h-3.5 w-3.5" />
            Phase 5 · Anomaly & Red-Flag Engine
          </div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-text sm:text-4xl">
            Procurement integrity signals
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
            Deterministic indicators, named multi-signal patterns, evidence status, and context notes.
            This surface prioritizes review leads; it does not make findings of misconduct.
          </p>
        </motion.div>

        <div className="mb-8 overflow-hidden rounded-2xl border border-border bg-surface/70 p-4 shadow-sm sm:p-5">
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") investigate();
                }}
                placeholder="Search a buyer, supplier, tender, or procurement entity…"
                className="h-11 w-full rounded-xl border border-border bg-bg px-10 text-sm text-text outline-none transition focus:border-accent/60"
              />
            </div>
            <Button
              onClick={investigate}
              disabled={!query.trim() || running}
              loading={running}
              icon={running ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
            >
              {running ? "Screening…" : "Screen for red flags"}
            </Button>
          </div>
        </div>

        {error && <ErrorState message={error} title="Red-flag screening failed" />}

        {!report && !running && !error && (
          <Section eyebrow="Engine contract" title="What this phase now exposes">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                [AlertTriangle, "Indicators", "Evidence-backed anomaly signals with explicit severity and confidence."],
                [GitBranch, "Patterns", "Named rule combinations rather than arithmetic risk sums."],
                [CheckCircle2, "Evidence state", "Verified, probable, or unknown — missing evidence never becomes a positive signal."],
                [Sparkles, "Context", "Emergency, disaster, correction, and other deterministic context adjustments."],
              ].map(([Icon, title, body]) => (
                <div key={String(title)} className="rounded-xl border border-border bg-bg-2/30 p-4">
                  <Icon className="h-4 w-4 text-accent" />
                  <div className="mt-3 text-sm font-semibold text-text">{title}</div>
                  <div className="mt-1 text-xs leading-relaxed text-faint">{body}</div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {running && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
            <div className="rounded-xl border border-accent/20 bg-accent/[0.05] p-4">
              <div className="flex items-center gap-3">
                <span className="relative grid h-8 w-8 place-items-center rounded-full border border-accent/30 bg-accent/10 text-accent">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </span>
                <div>
                  <div className="text-sm font-semibold text-text">Deterministic screening in progress</div>
                  <div className="mt-0.5 text-xs text-faint">Retrieving records → resolving entities → evaluating anomaly rules → classifying patterns</div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {report && risk && (
          <div className="space-y-8">
            <Section eyebrow="Verdict" title="Integrity screening result">
              <div className="grid gap-4 lg:grid-cols-[1.35fr_1fr]">
                <div className={`rounded-2xl border p-5 ${severityTone(risk.overall_severity)}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-80">Deterministic V2</div>
                      <div className="mt-2 text-3xl font-semibold capitalize">{risk.overall_severity}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] uppercase tracking-[0.14em] opacity-70">Score</div>
                      <div className="mt-1 text-3xl font-semibold tabular">{risk.overall_score}</div>
                    </div>
                  </div>
                  <p className="mt-4 max-w-3xl text-sm leading-relaxed opacity-85">{risk.summary}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Chip tone="neutral">{risk.indicators.length} indicators</Chip>
                    <Chip tone="neutral">{patterns.length} patterns</Chip>
                    <Chip tone="neutral">{Math.round((risk.confidence?.score ?? 0) * 100)}% evidence completeness</Chip>
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-bg-2/30 p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-faint">Assessment integrity</div>
                  <div className="mt-3 space-y-3 text-sm text-muted">
                    <div><span className="text-faint">Method:</span> {risk.method}</div>
                    <div><span className="text-faint">Confidence:</span> {risk.confidence?.level ?? "very_low"}</div>
                    <div><span className="text-faint">Records:</span> {report.package.records.length}</div>
                    <div><span className="text-faint">Last source retrieval:</span> {formatDate(report.package.timeline.at(-1)?.event_date ?? null)}</div>
                  </div>
                  <div className="mt-4 rounded-lg border border-border bg-bg px-3 py-2 text-[11px] leading-relaxed text-faint">
                    {risk.disclaimer}
                  </div>
                </div>
              </div>
            </Section>

            <AnimatePresence>
              {patterns.length > 0 && (
                <Section eyebrow="Pattern intelligence" title="Named multi-signal patterns">
                  <div className="grid gap-3 md:grid-cols-2">
                    {patterns.map((pattern: RiskPattern, index) => (
                      <motion.div
                        key={pattern.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.04 }}
                        className={`rounded-xl border p-4 ${severityTone(pattern.severity)}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] opacity-70">{pattern.severity}</div>
                            <div className="mt-1 text-sm font-semibold">{pattern.name}</div>
                          </div>
                          <GitBranch className="h-4 w-4 opacity-70" />
                        </div>
                        <div className="mt-3 rounded-lg border border-current/10 bg-black/[0.04] px-3 py-2 font-mono text-[10.5px] opacity-80">{pattern.rule}</div>
                        <p className="mt-3 text-xs leading-relaxed opacity-80">{pattern.reason}</p>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {pattern.indicators.map((indicator) => <Chip key={indicator} tone="neutral">{indicator}</Chip>)}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </Section>
              )}
            </AnimatePresence>

            <Section eyebrow="Indicators" title={`Triggered signals (${rankedIndicators.length})`}>
              {rankedIndicators.length === 0 ? (
                <EmptyState icon={<CheckCircle2 className="h-5 w-5" />} title="No indicators triggered" message="No configured procurement integrity indicator fired on the retrieved evidence." />
              ) : (
                <div className="space-y-2">
                  {rankedIndicators.map((indicator: RiskIndicatorV2) => {
                    const open = openId === indicator.id;
                    return (
                      <motion.div key={indicator.id} layout className="overflow-hidden rounded-xl border border-border bg-surface/60">
                        <button
                          type="button"
                          onClick={() => setOpenId(open ? null : indicator.id)}
                          className="flex w-full items-center gap-3 px-4 py-3.5 text-left"
                        >
                          <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${severityTone(indicator.severity)}`}>
                            {indicator.severity}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-semibold text-text">{indicator.name}</div>
                            <div className="mt-0.5 truncate text-xs text-faint">{indicator.reason}</div>
                          </div>
                          <Chip tone={evidenceTone(indicator.evidence_status)}>{indicator.evidence_status}</Chip>
                          <span className="tabular text-xs font-semibold text-text">{indicator.score}</span>
                          <ChevronDown className={`h-4 w-4 text-faint transition-transform ${open ? "rotate-180" : ""}`} />
                        </button>
                        <AnimatePresence initial={false}>
                          {open && (
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden border-t border-border">
                              <div className="grid gap-4 px-4 py-4 lg:grid-cols-2">
                                <div>
                                  <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Evidence & reasoning</div>
                                  <p className="mt-2 text-xs leading-relaxed text-muted">{indicator.reason}</p>
                                  <div className="mt-3 flex flex-wrap gap-1.5">
                                    <Chip tone="neutral">base {indicator.base_severity}</Chip>
                                    <Chip tone="neutral">confidence {Math.round(indicator.confidence * 100)}%</Chip>
                                    {indicator.review_required && <Chip tone="neutral">{indicator.review_note}</Chip>}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Supporting records</div>
                                  <div className="mt-2 max-h-32 overflow-auto text-xs text-muted">
                                    {indicator.supporting_records.length === 0 ? "No supporting record reference returned." : indicator.supporting_records.map((ref) => <div key={ref} className="py-1 font-mono">{ref}</div>)}
                                  </div>
                                </div>
                                {(indicator.context_notes.length > 0 || indicator.required_evidence.length > 0) && (
                                  <div className="lg:col-span-2 grid gap-3 md:grid-cols-2">
                                    <div className="rounded-lg border border-border bg-bg-2/30 p-3">
                                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Context applied</div>
                                      <ul className="mt-2 space-y-1 text-xs leading-relaxed text-muted">
                                        {indicator.context_notes.length ? indicator.context_notes.map((note) => <li key={note}>· {note}</li>) : <li>· None</li>}
                                      </ul>
                                    </div>
                                    <div className="rounded-lg border border-border bg-bg-2/30 p-3">
                                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">To confirm, obtain</div>
                                      <div className="mt-2 flex flex-wrap gap-1.5">
                                        {indicator.required_evidence.map((item) => <Chip key={item} tone="neutral">{item}</Chip>)}
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </Section>

            <Section eyebrow="Audit trail" title="Explainability tree">
              {risk.explainability.length === 0 ? (
                <EmptyState message="No explainability nodes returned." />
              ) : (
                <div className="space-y-2">
                  {risk.explainability.map((node) => (
                    <div key={node.indicator_id} className="rounded-xl border border-border bg-bg-2/30 p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="text-sm font-semibold text-text">{node.name}</div>
                        <Chip tone="neutral">base {node.base_severity} · {node.base_score}</Chip>
                        <Chip tone={evidenceTone(node.evidence_status)}>{node.evidence_status}</Chip>
                        <Chip tone="neutral">final {node.final_severity} · {node.score_contribution}</Chip>
                      </div>
                      <div className="mt-3 grid gap-3 text-xs md:grid-cols-3">
                        <div><div className="text-[10px] uppercase tracking-[0.15em] text-faint">Rule</div><div className="mt-1 text-muted">{node.rule_triggered}</div></div>
                        <div><div className="text-[10px] uppercase tracking-[0.15em] text-faint">Reason</div><div className="mt-1 text-muted">{node.reason}</div></div>
                        <div><div className="text-[10px] uppercase tracking-[0.15em] text-faint">Evidence refs</div><div className="mt-1 text-muted">{node.evidence.length} linked</div></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          </div>
        )}
      </div>
    </PageShell>
  );
}
