"use client";

import { useEffect, useState } from "react";
import { ClipboardCheck, Clock3, Inbox, ShieldAlert } from "lucide-react";
import { EmptyState } from "@/components/ui/states";
import { Section } from "@/components/ui/card";

const STORAGE_KEY = "sentry.review-handoff";

type Draft = {
  subject: string;
  review_reason: string;
  findings: string[];
  evidence_count: number;
  outstanding_evidence: string[];
  alternative_explanations: string[];
  reviewer_note: string;
  saved_at?: string;
};

export function ReviewInbox() {
  const [draft, setDraft] = useState<Draft | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setDraft(JSON.parse(raw) as Draft);
    } catch {
      setDraft(null);
    }
  }, []);

  return (
    <Section eyebrow="Government intake" title="Review queue" action={<Inbox className="h-4 w-4 text-accent" />}>
      {!draft ? (
        <EmptyState icon={<Inbox className="h-5 w-5" />} title="No review handoff received" message="Public or research workspaces can prepare an evidence-backed handoff. Submitted drafts appear here on the same analyst workstation." />
      ) : (
        <article className="rounded-xl border border-border bg-bg-2/40 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-semibold text-text">
                <span className="grid h-8 w-8 place-items-center rounded-lg border border-accent/25 bg-accent/10 text-accent"><ShieldAlert className="h-4 w-4" /></span>
                {draft.subject}
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted">{draft.review_reason}</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-warning">
              <Clock3 className="h-3 w-3" /> Pending human review
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <Metric label="Review leads" value={draft.findings.length} />
            <Metric label="Evidence items" value={draft.evidence_count} />
            <Metric label="Evidence outstanding" value={draft.outstanding_evidence.length} />
          </div>

          {draft.reviewer_note ? (
            <div className="mt-4 rounded-lg border border-border bg-surface/50 p-3">
              <div className="t-label">Submitter note</div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-text">{draft.reviewer_note}</p>
            </div>
          ) : null}

          <div className="mt-4 flex items-center gap-2 border-t border-border pt-3 text-[10.5px] text-faint">
            <ClipboardCheck className="h-3.5 w-3.5 text-accent" />
            Intake is a review handoff; no automated enforcement or adjudication is performed.
          </div>
        </article>
      )}
    </Section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-surface/60 p-3">
      <div className="t-label">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular text-text">{value}</div>
    </div>
  );
}
