"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileQuestion,
  ListChecks,
  ShieldCheck,
} from "lucide-react";

const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";

type NextAction = {
  id: string;
  title: string;
  owner: string;
  priority: string;
  rationale: string;
  evidence_needed: string[];
  completion_condition: string;
};

type Report = {
  schema_version: string;
  generated_at: string;
  outcome: "CORROBORATED" | "PARTIALLY_VERIFIED" | "INCONCLUSIVE" | string;
  lifecycle_state: string;
  execution_summary: {
    expected_total: number;
    observed_total: number;
    gap_total: number;
    observation_count: number;
    evidence_count: number;
    gps_evidence_count: number;
  };
  evidence_quality: {
    score: number;
    tier: "high" | "moderate" | "limited" | string;
    frame_coverage: number;
    gps_coverage: number;
    confidence_coverage: number;
    limitations: string[];
  };
  findings: {
    established: string[];
    not_established: string[];
  };
  alternative_explanations: string[];
  unresolved_questions: string[];
  next_actions: NextAction[];
  case_state: {
    automatic_close: boolean;
    investigator_decision_required: boolean;
    decision_options: string[];
  };
  verification_context: {
    mission_id: string;
    verification_objective: string;
    dispatch_reason: string;
    operator_id?: string | null;
    rover_id?: string | null;
  };
  provenance: {
    verification_version: number | null;
    report_hash: string;
  };
  guardrail: string;
};

type Payload = {
  tender: {
    id: string;
    reference_number: string;
    title: string;
    procuring_entity?: string | null;
    source_url?: string | null;
  };
  verification: {
    id: string;
    version: number;
    status: string;
    mission_id: string;
    submitted_at?: string | null;
  };
  report: Report;
};

const outcomeCopy: Record<string, { title: string; detail: string; icon: "warning" | "success" | "question" }> = {
  CORROBORATED: {
    title: "No observed shortfall",
    detail: "Returned field observations matched the listed requirement quantities. An investigator still needs to review the original procurement evidence before closing the question.",
    icon: "success",
  },
  PARTIALLY_VERIFIED: {
    title: "Reconciliation required",
    detail: "FIELD established a physical discrepancy signal, but the reason for the gap is not established by field evidence alone.",
    icon: "warning",
  },
  INCONCLUSIVE: {
    title: "Verification inconclusive",
    detail: "The returned mission evidence is insufficient to answer the physical verification question reliably.",
    icon: "question",
  },
};

export function FieldVerificationCloseout({ tenderKey }: { tenderKey?: string }) {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!tenderKey) return;
    setLoading(true);
    try {
      const response = await fetch(
        BACKEND + "/api/investigations/tenders/" + encodeURIComponent(tenderKey) + "/field-verification-report",
        { cache: "no-store" },
      );
      if (!response.ok) {
        if (response.status === 404) {
          setPayload(null);
          return;
        }
        throw new Error("FIELD report request failed");
      }
      setPayload((await response.json()) as Payload);
    } catch {
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [tenderKey]);

  useEffect(() => {
    void load();
    const refresh = () => void load();
    window.addEventListener("sentry.field.report.updated", refresh);
    return () => window.removeEventListener("sentry.field.report.updated", refresh);
  }, [load]);

  const report = payload?.report;
  const copy = report ? outcomeCopy[report.outcome] || outcomeCopy.INCONCLUSIVE : null;
  const qualityLabel = useMemo(
    () => report?.evidence_quality?.tier?.toUpperCase() || "—",
    [report],
  );

  if (!tenderKey || (!payload && !loading)) return null;

  if (!report) {
    return (
      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:p-6">
        <div className="flex items-center gap-2 text-xs text-muted">
          <ClipboardCheck className="h-4 w-4 text-accent" />
          {loading ? "Building FIELD closeout report…" : "No durable FIELD closeout report yet."}
        </div>
      </section>
    );
  }

  const Icon = copy?.icon === "warning"
    ? AlertTriangle
    : copy?.icon === "success"
      ? CheckCircle2
      : FileQuestion;

  return (
    <section className="overflow-hidden rounded-2xl border border-accent/20 bg-surface shadow-sm">
      <header className="border-b border-accent/15 bg-accent/[0.035] px-5 py-5 md:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.18em] text-accent">
              <ShieldCheck className="h-3.5 w-3.5" />
              FIELD → SENTRY / INVESTIGATION CLOSEOUT
            </div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-text">
              Physical evidence has a next step
            </h2>
            <p className="mt-1 max-w-4xl text-sm leading-6 text-muted">
              {report.verification_context.dispatch_reason}
            </p>
          </div>
          <div className="inline-flex shrink-0 items-center gap-2 rounded-full border border-border bg-bg/25 px-3 py-1.5 text-xs font-semibold text-text">
            <Icon className="h-3.5 w-3.5" />
            {copy?.title || report.outcome}
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric label="Expected" value={report.execution_summary.expected_total} />
          <Metric label="Observed" value={report.execution_summary.observed_total} />
          <Metric label="Gap" value={report.execution_summary.gap_total} />
          <Metric label="Evidence frames" value={report.execution_summary.evidence_count} />
          <Metric label="Evidence quality" value={qualityLabel} />
        </div>
      </header>

      <div className="grid gap-5 p-5 md:p-6 xl:grid-cols-[1.05fr_.95fr]">
        <ReportList
          icon={<CheckCircle2 className="h-4 w-4" />}
          title="What FIELD established"
          items={report.findings.established}
        />
        <ReportList
          icon={<FileQuestion className="h-4 w-4" />}
          title="What remains unknown"
          items={report.unresolved_questions}
        />
      </div>

      <div className="grid gap-5 border-t border-border px-5 py-5 md:grid-cols-2 md:px-6">
        <ReportList
          icon={<AlertTriangle className="h-4 w-4" />}
          title="Alternative explanations to test"
          items={report.alternative_explanations}
        />
        <ReportList
          icon={<ClipboardCheck className="h-4 w-4" />}
          title="Not established by FIELD"
          items={report.findings.not_established}
        />
      </div>

      <div className="border-t border-border px-5 py-5 md:px-6">
        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.15em] text-faint">
          <ListChecks className="h-3.5 w-3.5" />
          Next actions
        </div>
        <div className="mt-3 grid gap-3 xl:grid-cols-2">
          {report.next_actions.map((action) => (
            <article key={action.id} className="rounded-xl border border-border bg-bg/10 p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="text-sm font-semibold text-text">{action.title}</div>
                  <div className="mt-1 text-xs text-muted">{action.rationale}</div>
                </div>
                <span className="inline-flex shrink-0 rounded-full border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase tracking-[.12em] text-accent">
                  {action.priority}
                </span>
              </div>
              <div className="mt-3 grid gap-3 text-xs text-muted md:grid-cols-2">
                <div>
                  <div className="font-semibold text-text">Owner</div>
                  <div className="mt-1">{action.owner}</div>
                </div>
                <div>
                  <div className="font-semibold text-text">Completion condition</div>
                  <div className="mt-1">{action.completion_condition}</div>
                </div>
              </div>
              <div className="mt-3">
                <div className="font-semibold text-text text-xs">Evidence needed</div>
                <div className="mt-1 space-y-1">
                  {action.evidence_needed.map((item) => (
                    <div key={item} className="text-xs leading-5 text-muted">• {item}</div>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>

      <footer className="border-t border-border bg-bg/10 px-5 py-4 text-xs text-muted md:px-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            Mission <span className="font-semibold text-text">{report.verification_context.mission_id}</span>
            {" · "}
            Version <span className="font-semibold text-text">{report.provenance.verification_version ?? payload.verification.version}</span>
            {" · "}
            {report.evidence_quality.score}/100 evidence provenance score
          </div>
          <div className="font-medium text-text">Investigator decision required · automatic close: no</div>
        </div>
        <p className="mt-2 border-t border-border pt-2 leading-5">{report.guardrail}</p>
      </footer>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl border border-border bg-bg/10 p-3">
      <div className="text-[10px] uppercase tracking-[.13em] text-faint">{label}</div>
      <div className="mt-1.5 text-xl font-semibold text-text">{value}</div>
    </div>
  );
}

function ReportList({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.14em] text-faint">
        {icon}
        {title}
      </div>
      <div className="mt-3 space-y-2">
        {items.length ? (
          items.map((item) => (
            <div key={item} className="rounded-lg border border-border bg-bg/10 px-3 py-2 text-xs leading-5 text-muted">
              {item}
            </div>
          ))
        ) : (
          <div className="text-xs text-muted">No items returned.</div>
        )}
      </div>
    </div>
  );
}
