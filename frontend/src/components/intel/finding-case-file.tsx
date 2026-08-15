"use client";

/**
 * FindingCaseFile — one case file per finding, the core unit of the workspace.
 *
 * Every finding answers the five investigator questions, in order:
 *   1. What did SENTRY detect?             (the deterministic detection, verbatim)
 *   2. What evidence supports it?          (supporting records + official source)
 *   3. What legitimate explanation could also explain it?  (evidence-backed only)
 *   4. What evidence is still required?    (routine vs escalation discriminators)
 *   5. What should the investigator investigate next?      (with a reason)
 *
 * Closed by the fixed Current Position — investigator language, no conclusions.
 * This card consolidates what previously lived in three separate sections
 * (indicators, investigator review, evidence challenge) so a finding appears
 * exactly once in the workspace.
 */
import { motion } from "framer-motion";
import { ArrowRight, BookOpenCheck, ChevronRight, CircleHelp, ExternalLink, FileText, Loader2, Scale, ScanSearch } from "lucide-react";
import { useCallback, useState } from "react";

import {
  getContextAnalysis,
  type ContextFactsPayload,
  type FindingChallenge,
  type ProcurementContextAnalysis
} from "@/lib/api";
import { DURATION, EASE } from "@/lib/motion";

export type OfficialSource = { ref: string; url: string; source: string };

export type NextStep = { label: string; query: string; reason: string };

export type CaseFileFinding = {
  id: string;
  name: string;
  severity: "low" | "medium" | "high" | "critical";
  reason: string;
  evidenceStatus: string;
  recordRefs: string[];
  contextNotes: string[];
};

/* Severity reads off the ordinal risk lattice, never off the emerald accent —
   emerald means "action available", not "low risk". */
const PRIORITY_PILL: Record<CaseFileFinding["severity"], { label: string; cls: string }> = {
  critical: { label: "Critical priority", cls: "border-risk-crit/60 bg-risk-crit/15 text-risk-crit" },
  high: { label: "High priority", cls: "border-risk-high/40 bg-risk-high/10 text-risk-high" },
  medium: { label: "Medium priority", cls: "border-risk-med/40 bg-risk-med/10 text-risk-med" },
  low: { label: "Low priority", cls: "border-risk-low/40 bg-risk-low/10 text-risk-low" }
};

const CURRENT_POSITION_FALLBACK =
  "The available evidence does not yet distinguish between routine procurement activity " +
  "and procurement requiring escalation. Additional evidence is required.";

/**
 * Investigator-grade presentation of the analyzer's deterministic applicability
 * classification. Pure display mapping — the backend vocabulary is unchanged.
 * Never implies certainty, guilt, or that the finding is false.
 */
const APPLICABILITY_DISPLAY: Record<string, { badge: string; note: string; tone: string }> = {
  "Directly supported by retrieved evidence": {
    badge: "Supported by retrieved evidence",
    note: "",
    tone: "border-success/40 bg-success/10 text-success"
  },
  "Potentially applicable based on retrieved evidence": {
    badge: "Official procurement guidance identified",
    note: "Additional evidence is required before applicability can be confirmed.",
    tone: "border-accent/40 bg-accent/10 text-accent"
  },
  "Applicability cannot be established from available evidence": {
    badge: "Applicability not yet determined",
    note: "Current evidence is insufficient to determine whether the guidance applies to this case.",
    tone: "border-border bg-surface text-muted"
  }
};

/** Guidance provenance badge. Guidance from allowlisted procurement authorities
 * is OFFICIAL guidance — the internal review-lifecycle state is never shown as
 * "draft" to an investigator. */
const GUIDANCE_BADGE: Record<string, { label: string; tone: string }> = {
  verified: { label: "Verified Procurement Guidance", tone: "border-success/40 bg-success/10 text-success" },
  draft: { label: "Official Procurement Guidance", tone: "border-accent/40 bg-accent/10 text-accent" }
};

/**
 * Document-driven investigation: the records an investigator should obtain,
 * per finding type. Deterministic domain checklists (standard procurement-file
 * documents) — only documents relevant to the finding type are shown.
 */
const REQUIRED_DOCUMENTS: Record<string, string[]> = {
  contract_fragmentation: [
    "Administrative Sanction",
    "Technical Sanction",
    "Detailed Project Report (DPR)",
    "Estimate File",
    "Approval Note",
    "Tender Committee Minutes"
  ],
  single_bidder: [
    "Bid Opening Register",
    "Comparative Bid Statement",
    "Tender Committee Minutes",
    "Single-Bid Justification / Approval Note",
    "NIT & Publication Proof"
  ],
  high_value_direct_award: [
    "Administrative Sanction",
    "Financial Concurrence",
    "Nomination / Direct-Award Justification",
    "Approval Note"
  ],
  repeat_supplier: [
    "Comparative Bid Statement",
    "Bid Opening Register",
    "Framework Agreement (if applicable)",
    "Tender Committee Minutes"
  ],
  award_clustering: [
    "Administrative Sanction",
    "Financial Concurrence",
    "Budget Release / Sanction Notes",
    "Approval Note"
  ],
  buyer_concentration: ["Bid Opening Register", "Comparative Bid Statement", "Pre-Qualification Criteria"],
  supplier_concentration: ["Comparative Bid Statement", "Supplier Registration / Capability Documents"],
  suspicious_timing: ["Tender Opening Register", "Evaluation Minutes", "Corrigendum Records"],
  missing_award_data: ["Award Notice", "Signed Contract / Letter of Award"],
  missing_documents: ["NIT", "BOQ", "Corrigendum (from official portal)"],
  abnormal_value: ["Estimate File", "BOQ", "Comparative Bid Statement", "Amendment Records"],
  high_value: ["Estimate File", "BOQ", "Comparative Bid Statement"],
  award_value_exceeds_tender: ["Estimate File", "Comparative Bid Statement", "Amendment Records"]
};

const REQUIRED_DOCUMENTS_DEFAULT = ["Approval Note", "Evaluation Record"];

export function FindingCaseFile({
  finding,
  challenge,
  sources,
  nextSteps,
  index,
  onInvestigate,
  contextFacts,
  triggerFacts = []
}: {
  finding: CaseFileFinding;
  challenge: FindingChallenge | null;
  sources: OfficialSource[];
  nextSteps: NextStep[];
  index: number;
  onInvestigate: (query: string) => void;
  /** Retrieved investigation facts for applicability evaluation of guidance. */
  contextFacts?: ContextFactsPayload;
  /** Deterministic fact chain explaining why the engine raised this finding. */
  triggerFacts?: string[];
}) {
  const pill = PRIORITY_PILL[finding.severity] ?? PRIORITY_PILL.medium;
  const primarySource = sources[0];

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 6) * 0.05, duration: DURATION.base, ease: EASE }}
      className="overflow-hidden rounded-2xl border border-border bg-bg-2/40 transition-colors duration-200 hover:border-border-strong"
    >
      {/* ── finding header ── */}
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-surface/40 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-accent/30 bg-accent/[0.08] text-accent">
            <ScanSearch className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-[15px] font-semibold text-text">{finding.name}</h3>
            <div className="mt-0.5 text-[11.5px] text-faint">
              {finding.recordRefs.length} supporting record{finding.recordRefs.length === 1 ? "" : "s"} · evidence{" "}
              {finding.evidenceStatus || "recorded"}
            </div>
          </div>
        </div>
        <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${pill.cls}`}>
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          {pill.label}
        </span>
      </header>

      <div className="space-y-6 p-5">
        {/* 1 — what SENTRY detected */}
        <section>
          <StepLabel n={1} text="What SENTRY detected" />
          <p className="mt-2 text-[13.5px] leading-relaxed text-text">{finding.reason}</p>
          {finding.contextNotes.length > 0 && (
            <ul className="mt-2.5 space-y-1.5">
              {finding.contextNotes.map((note, i) => (
                <li key={i} className="flex items-start gap-2 text-[11.5px] leading-relaxed text-faint">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted" />
                  {note}
                </li>
              ))}
            </ul>
          )}

          {/* why was this finding triggered? — deterministic fact chain only */}
          {triggerFacts.length > 0 && (
            <details className="group mt-3 rounded-lg border border-border bg-surface/40 px-3 py-2">
              <summary className="cursor-pointer list-none text-[11.5px] font-semibold text-muted transition-colors hover:text-text">
                <ChevronRight className="mr-1 inline h-3 w-3 transition-transform group-open:rotate-90" />
                Why was this finding triggered?
              </summary>
              <ol className="mt-2.5 space-y-1 pb-1.5">
                {triggerFacts.map((fact, i) => (
                  <li key={i} className="flex items-center gap-1.5 text-[12px] text-muted">
                    {i > 0 && <span className="text-faint">↓</span>}
                    <span className={i === triggerFacts.length - 1 ? "font-semibold text-text" : ""}>{fact}</span>
                  </li>
                ))}
              </ol>
              <p className="pb-1 text-[10px] leading-relaxed text-faint">
                Deterministic facts from the official procurement records — no probabilities, no model reasoning.
              </p>
            </details>
          )}
        </section>

        {/* 2 — evidence supporting investigation */}
        <section>
          <StepLabel n={2} text="Evidence supporting investigation" />
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            {finding.recordRefs.slice(0, 6).map((ref) => (
              <span key={ref} className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 font-mono text-[11px] text-muted">
                <FileText className="h-3 w-3" /> {ref}
              </span>
            ))}
            {finding.recordRefs.length > 6 && (
              <span className="text-[11px] text-faint">+{finding.recordRefs.length - 6} more</span>
            )}
            {primarySource && (
              <a
                href={primarySource.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-accent/40 bg-accent/[0.08] px-2.5 py-1 text-[11px] font-semibold text-accent transition-colors duration-200 hover:bg-accent/15"
              >
                <ExternalLink className="h-3 w-3" />
                Official record
                {sources.length > 1 ? ` (${sources.length})` : ""}
              </a>
            )}
          </div>
        </section>

        {/* 3 — possible legitimate explanations (evidence-backed only) */}
        <section>
          <StepLabel n={3} text="Possible legitimate explanations" icon={<Scale className="h-3 w-3 text-success" />} />
          {challenge && challenge.explanations.length > 0 ? (
            <ul className="mt-2.5 space-y-2">
              {challenge.explanations.map((e, i) => (
                <li key={i} className="rounded-lg border border-success/25 bg-success/[0.04] px-3 py-2.5">
                  <div className="text-[13px] leading-relaxed text-text">{e.explanation}</div>
                  <div className="mt-1 text-[11.5px] leading-relaxed text-muted">Evidence: {e.evidence}</div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs leading-relaxed text-faint">
              No evidence-backed legitimate explanation was detected in the retrieved records.
            </p>
          )}
        </section>

        {/* 4 — evidence still required */}
        <section>
          <StepLabel n={4} text="Evidence still required" icon={<CircleHelp className="h-3 w-3 text-accent" />} />
          {challenge && challenge.questions.length > 0 ? (
            <ul className="mt-2.5 space-y-2">
              {challenge.questions.map((q, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                  <span className="min-w-0">
                    <span className="block text-[13px] leading-relaxed text-text">{q.question}</span>
                    <span className="block truncate text-[10px] text-faint">tests: {q.eliminates}</span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs leading-relaxed text-faint">Obtain the award and evaluation records for the flagged tenders.</p>
          )}

          {/* required documents — the procurement-file records that answer the
              questions above, specific to this finding type */}
          <div className="mt-3.5 rounded-lg border border-border bg-surface/50 px-3 py-2.5">
            <div className="t-label">Required documents</div>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {(REQUIRED_DOCUMENTS[finding.id] ?? REQUIRED_DOCUMENTS_DEFAULT).map((doc) => (
                <li key={doc} className="rounded-md border border-border bg-bg-2/50 px-2 py-0.5 text-[11px] text-muted">
                  {doc}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* procurement context — trusted-authority guidance, retrieved on demand
            and evaluated against the retrieved facts before display.
            Read-only and additive: it never alters the finding above. */}
        <ProcurementContextBlock findingId={finding.id} findingName={finding.name} facts={contextFacts} />

        {/* 5 — recommended next investigation */}
        {nextSteps.length > 0 && (
          <section>
            <StepLabel n={5} text="Recommended next investigation" />
            <div className="mt-2.5 flex flex-col gap-2">
              {nextSteps.map((step, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onInvestigate(step.query)}
                  className="group flex items-center justify-between gap-3 rounded-xl border border-border bg-surface/50 px-3.5 py-2.5 text-left transition-colors duration-200 hover:border-accent/40"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-text group-hover:text-accent">{step.label}</span>
                    <span className="mt-0.5 block truncate text-[11.5px] text-faint">{step.reason}</span>
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted transition-all group-hover:translate-x-0.5 group-hover:text-accent" />
                </button>
              ))}
            </div>
          </section>
        )}
      </div>

      {/* ── current position (fixed decision boundary) ── */}
      <footer className="border-t border-border/60 bg-surface/40 px-5 py-3.5">
        <div className="t-label">Current position</div>
        <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{challenge?.position ?? CURRENT_POSITION_FALLBACK}</p>
      </footer>
    </motion.article>
  );
}

/**
 * Procurement context from trusted authorities (Verified Context Engine).
 * Collapsed by default; fetched once on first expand — never cached server-side,
 * never altering the finding. Guidance from allowlisted procurement authorities
 * is presented as Official Procurement Guidance with its applicability status.
 */
function ProcurementContextBlock({
  findingId,
  findingName,
  facts
}: {
  findingId: string;
  findingName: string;
  facts?: ContextFactsPayload;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<ProcurementContextAnalysis | null>(null);
  const [failed, setFailed] = useState(false);

  const toggle = useCallback(() => {
    setOpen((v) => !v);
    if (!analysis && !loading && !failed) {
      setLoading(true);
      getContextAnalysis(findingId, findingName, facts)
        .then(setAnalysis)
        .catch(() => setFailed(true))
        .finally(() => setLoading(false));
    }
  }, [analysis, loading, failed, findingId, findingName, facts]);

  return (
    <section className="rounded-xl border border-border bg-surface/40">
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left"
      >
        <span className="t-label flex items-center gap-1.5">
          <BookOpenCheck className="h-3 w-3 text-accent" /> Procurement context · trusted authorities
        </span>
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted" />
        ) : (
          <ChevronRight className={`h-3.5 w-3.5 text-muted transition-transform duration-200 ${open ? "rotate-90" : ""}`} />
        )}
      </button>

      {open && (
        <div className="space-y-3 border-t border-border/60 px-3.5 py-3">
          {failed ? (
            <p className="text-xs text-faint">Procurement context could not be retrieved.</p>
          ) : !analysis ? (
            <p className="text-xs text-faint">Consulting trusted procurement authorities…</p>
          ) : !analysis.guidance_available ? (
            <div className="space-y-1.5">
              <p className="text-xs text-muted">{analysis.potential_context}</p>
              {analysis.applicability_notes.map((note, n) => (
                <p key={n} className="text-[11px] leading-snug text-faint">{note}</p>
              ))}
            </div>
          ) : (
            <>
              <p className="text-[13px] leading-snug text-text">{analysis.potential_context}</p>
              {analysis.guidance.map((g, i) => (
                <div key={i} className="rounded-lg border border-border bg-bg-2/40 px-2.5 py-2">
                  {/* deterministic applicability classification — evidence-driven,
                      rendered in investigator-grade language (display-only mapping) */}
                  <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                    {(() => {
                      const display = APPLICABILITY_DISPLAY[g.applicability_status] ?? {
                        badge: g.applicability_status,
                        note: "",
                        tone: "border-border bg-surface text-muted"
                      };
                      const provenance = GUIDANCE_BADGE[g.card_status];
                      return (
                        <>
                          <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${display.tone}`}>
                            {display.badge}
                          </span>
                          {provenance && (
                            <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${provenance.tone}`}>
                              {provenance.label}
                            </span>
                          )}
                        </>
                      );
                    })()}
                  </div>
                  <p className="text-[13px] leading-snug text-text">{g.supporting_guidance}</p>
                  {g.applicability_evidence ? (
                    <p className="mt-1 text-[11px] leading-snug text-success">
                      Evidence: {g.applicability_evidence}
                    </p>
                  ) : (
                    APPLICABILITY_DISPLAY[g.applicability_status]?.note && (
                      <p className="mt-1 text-[11px] leading-snug text-faint">
                        {APPLICABILITY_DISPLAY[g.applicability_status].note}
                      </p>
                    )
                  )}
                  <div className="mt-1.5 grid gap-x-4 gap-y-0.5 text-[11px] text-muted sm:grid-cols-2">
                    <span><span className="text-faint">Authority:</span> {g.authority}</span>
                    <span><span className="text-faint">Source type:</span> {g.source_type}</span>
                    <span className="sm:col-span-2"><span className="text-faint">Reference:</span> {g.reference}</span>
                    <span className="sm:col-span-2"><span className="text-faint">Applicability:</span> {g.applicability}</span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    {g.source_urls.map((url, u) => (
                      <a key={u} href={url} target="_blank" rel="noreferrer"
                         className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:underline">
                        <ExternalLink className="h-3 w-3" /> Official source
                      </a>
                    ))}
                  </div>
                </div>
              ))}
              {analysis.applicability_notes.length > 0 && (
                <div className="rounded-lg border border-border bg-surface/50 px-2.5 py-2">
                  {analysis.applicability_notes.map((note, n) => (
                    <p key={n} className="text-[11px] leading-snug text-faint">{note}</p>
                  ))}
                </div>
              )}
              <p className="text-[11px] leading-snug text-faint">{analysis.current_assessment}</p>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function StepLabel({ n, text, icon }: { n: number; text: string; icon?: React.ReactNode }) {
  return (
    <div className="t-label flex items-center gap-2">
      <span className="grid h-[18px] w-[18px] place-items-center rounded-full border border-border bg-surface text-[9px] text-muted">
        {n}
      </span>
      {icon}
      {text}
    </div>
  );
}
