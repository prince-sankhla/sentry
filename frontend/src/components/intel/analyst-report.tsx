"use client";

/**
 * AnalystReportSections — professional rendering of the grounded, structured
 * analyst report (procurement patterns, buyer / supplier / award / timeline
 * analysis, contradictions, missing evidence, and a derived confidence
 * assessment). Every value shown is a grounded projection of the Investigation
 * Package produced by the backend; this component only presents it.
 */

import { motion } from "framer-motion";

import { Section } from "@/components/ui/card";
import type {
  AnalystReport,
  ConfidenceAssessment,
  Contradiction
} from "@/lib/api";

export function AnalystReportSections({ report }: { report: AnalystReport }) {
  return (
    <div className="space-y-5">
      {report.confidence_assessment && <ConfidenceCard confidence={report.confidence_assessment} />}
      {report.contradictions.length > 0 && <ContradictionsCard contradictions={report.contradictions} />}
      {report.procurement_patterns.length > 0 && <PatternsCard patterns={report.procurement_patterns} />}
      {report.buyer_analysis.length > 0 && <BuyersCard buyers={report.buyer_analysis} />}
      {report.supplier_analysis.length > 0 && <SuppliersCard suppliers={report.supplier_analysis} />}
      {report.award_analysis && <AwardsCard award={report.award_analysis} />}
      {report.timeline_analysis && <TimelineCard timeline={report.timeline_analysis} />}
      {report.missing_evidence.length > 0 && <MissingEvidenceCard gaps={report.missing_evidence} />}
    </div>
  );
}

/* ----------------------------------------------------------------- confidence */

const CONF_TONE: Record<ConfidenceAssessment["level"], string> = {
  high: "text-success",
  moderate: "text-accent",
  low: "text-warning",
  very_low: "text-danger"
};

function ConfidenceCard({ confidence }: { confidence: ConfidenceAssessment }) {
  const pct = Math.round(confidence.score * 100);
  return (
    <Section eyebrow="Confidence" title="Confidence assessment">
      <div className="flex flex-wrap items-baseline gap-3">
        <span className={`text-3xl font-semibold tabular-nums ${CONF_TONE[confidence.level]}`}>{pct}%</span>
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">
          {confidence.level.replace("_", " ")}
        </span>
      </div>
      <p className="mt-2 text-sm text-muted">{confidence.explanation}</p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {confidence.dimensions.map((d) => (
          <div key={d.key} className="rounded-[12px] border border-border bg-bg-2/40 p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-text">{d.label}</span>
              <span className="text-xs tabular-nums text-muted">{Math.round(d.score * 100)}%</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface">
              <motion.div
                className="h-full rounded-full bg-accent/70"
                initial={{ width: 0 }}
                animate={{ width: `${Math.round(d.score * 100)}%` }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <p className="mt-1.5 text-[11px] leading-snug text-faint">{d.detail}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* -------------------------------------------------------------- contradictions */

const SEV_TONE: Record<Contradiction["severity"], string> = {
  high: "border-danger/40 bg-danger/[0.07] text-danger",
  medium: "border-warning/40 bg-warning/[0.07] text-warning",
  low: "border-border-strong bg-surface-2 text-muted"
};

function ContradictionsCard({ contradictions }: { contradictions: Contradiction[] }) {
  return (
    <Section
      eyebrow="Integrity"
      title="Contradictions & inconsistencies"
     
      action={<span className="text-xs text-faint">{contradictions.length} detected</span>}
    >
      <ul className="space-y-2">
        {contradictions.map((c, i) => (
          <li key={i} className="rounded-[12px] border border-border bg-bg-2/40 p-3">
            <div className="flex items-start gap-2.5">
              <span
                className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${SEV_TONE[c.severity]}`}
              >
                {c.severity}
              </span>
              <div className="min-w-0">
                <p className="text-sm text-text">{c.summary}</p>
                {c.detail && <p className="mt-0.5 text-xs text-faint">{c.detail}</p>}
                <div className="mt-1 flex flex-wrap gap-1.5 text-[10px] text-faint">
                  <span className="rounded bg-surface px-1.5 py-0.5">{c.type.replace(/_/g, " ")}</span>
                  {c.related_tenders.map((t) => (
                    <span key={t} className="rounded bg-surface px-1.5 py-0.5 font-mono">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}

/* ------------------------------------------------------------------ patterns */

function PatternsCard({ patterns }: { patterns: AnalystReport["procurement_patterns"] }) {
  return (
    <Section eyebrow="Signals" title="Procurement patterns">
      <ul className="space-y-2">
        {patterns.map((p, i) => (
          <li key={i} className="flex items-start gap-2.5 rounded-[12px] border border-border bg-bg-2/40 p-3">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-text">{p.pattern}</p>
              <p className="text-xs text-faint">{p.detail}</p>
              {p.supporting_tenders.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {p.supporting_tenders.map((t) => (
                    <span key={t} className="rounded bg-surface px-1.5 py-0.5 text-[10px] font-mono text-faint">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}

/* ------------------------------------------------------------------ buyers */

function BuyersCard({ buyers }: { buyers: AnalystReport["buyer_analysis"] }) {
  return (
    <Section eyebrow="Demand side" title="Buyer analysis">
      <div className="space-y-2">
        {buyers.map((b) => (
          <div key={b.name} className="rounded-[12px] border border-border bg-bg-2/40 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-semibold text-text">{b.name}</span>
              <span className="text-[11px] text-faint">
                {b.tender_count} tenders · {b.award_count} awards
                {b.total_award_value ? ` · ${b.total_award_value}` : ""}
              </span>
            </div>
            {b.top_suppliers.length > 0 && (
              <p className="mt-1 text-xs text-faint">
                Top suppliers: {b.top_suppliers.join(", ")}
                {b.concentration_pct != null ? ` · top share ${b.concentration_pct}%` : ""}
              </p>
            )}
            {b.note && <p className="mt-1 text-xs text-warning">{b.note}</p>}
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------------ suppliers */

function SuppliersCard({ suppliers }: { suppliers: AnalystReport["supplier_analysis"] }) {
  return (
    <Section eyebrow="Supply side" title="Supplier analysis">
      <div className="space-y-2">
        {suppliers.map((s) => (
          <div key={s.name} className="rounded-[12px] border border-border bg-bg-2/40 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-semibold text-text">{s.name}</span>
              <span className="text-[11px] text-faint">
                {s.award_count} awards{s.total_award_value ? ` · ${s.total_award_value}` : ""}
              </span>
            </div>
            {s.buyers.length > 0 && <p className="mt-1 text-xs text-faint">Buyers: {s.buyers.join(", ")}</p>}
            {s.note && <p className="mt-1 text-xs text-warning">{s.note}</p>}
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------------ awards */

function AwardsCard({ award }: { award: NonNullable<AnalystReport["award_analysis"]> }) {
  return (
    <Section eyebrow="Contracts" title="Award analysis">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Awards" value={String(award.total_awards)} />
        <Stat label="Valued" value={String(award.valued_awards)} />
        <Stat label="Total value" value={award.total_value ?? "—"} />
        <Stat label="Largest" value={award.largest_award_value ?? "—"} />
      </div>
      {award.note && <p className="mt-2 text-xs text-muted">{award.note}</p>}
    </Section>
  );
}

/* ------------------------------------------------------------------ timeline */

function TimelineCard({ timeline }: { timeline: NonNullable<AnalystReport["timeline_analysis"]> }) {
  return (
    <Section eyebrow="Chronology" title="Timeline analysis">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Events" value={String(timeline.event_count)} />
        <Stat label="First" value={timeline.first_event ?? "—"} />
        <Stat label="Last" value={timeline.last_event ?? "—"} />
        <Stat label="Fast awards" value={String(timeline.fast_awards)} />
      </div>
      {timeline.note && <p className="mt-2 text-xs text-muted">{timeline.note}</p>}
    </Section>
  );
}

/* ------------------------------------------------------------ missing evidence */

function MissingEvidenceCard({ gaps }: { gaps: string[] }) {
  return (
    <Section eyebrow="Gaps" title="Missing evidence">
      <ul className="space-y-1.5">
        {gaps.map((g, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-muted">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warning" />
            {g}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[12px] border border-border bg-bg-2/40 p-2.5">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-0.5 truncate text-sm font-semibold text-text" title={value}>
        {value}
      </div>
    </div>
  );
}
