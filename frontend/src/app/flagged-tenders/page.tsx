import Link from "next/link";
import { AlertTriangle, ArrowRight, Flag, ShieldAlert } from "lucide-react";

import { getRisk, type RiskSignal } from "@/lib/api";
import { PageHeader, PageShell, SeverityBadge } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

type FlaggedTender = {
  tenderId: string;
  reference: string;
  title: string;
  buyer: string;
  severity: "low" | "medium" | "high";
  score: number;
  signals: RiskSignal[];
};

function groupFlaggedTenders(signals: RiskSignal[]): FlaggedTender[] {
  const groups = new Map<string, FlaggedTender>();
  for (const signal of signals) {
    if (!signal.tender_id) continue;
    const key = signal.tender_id;
    const current = groups.get(key);
    if (!current) {
      groups.set(key, {
        tenderId: key,
        reference: signal.tender_reference ?? key,
        title: signal.title,
        buyer: signal.buyer ?? "Buyer not available",
        severity: signal.severity,
        score: signal.score,
        signals: [signal],
      });
      continue;
    }
    current.signals.push(signal);
    current.score = Math.max(current.score, signal.score);
    const rank = { low: 1, medium: 2, high: 3 } as const;
    if (rank[signal.severity] > rank[current.severity]) current.severity = signal.severity;
    if (signal.tender_reference) current.reference = signal.tender_reference;
  }
  return [...groups.values()].sort((a, b) => b.score - a.score);
}

export default async function FlaggedTendersPage() {
  let data;
  try {
    data = await getRisk();
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Review Queue" title="Flagged Tenders" subtitle="Tender-level review signals that need investigator attention." />
        <ErrorState title="Flagged tender queue unavailable" message="SENTRY could not load the current review signals." />
      </PageShell>
    );
  }

  const tenders = groupFlaggedTenders(data.signals);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Review Queue"
        title="Flagged Tenders"
        subtitle="Only tender-linked screening signals appear here. These are review leads, not findings of wrongdoing."
        actions={
          <Link href="/risk" className="inline-flex h-10 items-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text hover:border-border-strong">
            Full signal assessment <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Flagged tenders" value={formatNumber(tenders.length)} />
        <Stat label="High severity" value={formatNumber(tenders.filter((item) => item.severity === "high").length)} />
        <Stat label="Medium severity" value={formatNumber(tenders.filter((item) => item.severity === "medium").length)} />
        <Stat label="Signals" value={formatNumber(data.signals.filter((item) => item.tender_id).length)} />
      </div>

      {tenders.length === 0 ? (
        <EmptyState
          icon={<ShieldAlert className="h-5 w-5" />}
          title="No flagged tender leads"
          message="No current risk signal is linked directly to a tender in the available dataset."
        />
      ) : (
        <div className="space-y-3">
          {tenders.map((tender) => (
            <article key={tender.tenderId} className="rounded-2xl border border-border bg-surface p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.13em] text-warning">
                      <Flag className="h-3 w-3" /> Flagged for review
                    </span>
                    <SeverityBadge severity={tender.severity} score={tender.score} />
                  </div>
                  <h2 className="mt-3 text-lg font-semibold text-text">{tender.title}</h2>
                  <div className="mt-1 font-mono text-xs text-faint">{tender.reference}</div>
                  <div className="mt-2 text-sm text-muted">Buyer: {tender.buyer}</div>
                </div>
                <Link href={"/tenders/" + tender.tenderId} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-border bg-bg-2 px-3.5 py-2 text-xs font-semibold text-text hover:border-border-strong">
                  Open tender <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>

              <div className="mt-4 grid gap-2 md:grid-cols-2">
                {tender.signals.map((signal, index) => (
                  <div key={signal.type + "-" + index} className="rounded-xl border border-border bg-bg-2/40 p-3">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-text">{signal.title}</div>
                        <div className="mt-1 text-xs leading-5 text-muted">{signal.summary}</div>
                        {signal.evidence.length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {signal.evidence.map((evidence, evidenceIndex) => (
                              <span key={evidenceIndex} className="rounded-md border border-border bg-surface px-2 py-1 text-[10px] text-muted">{evidence}</span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </PageShell>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="text-[10px] font-semibold uppercase tracking-[.13em] text-faint">{label}</div>
      <div className="mt-1.5 text-2xl font-semibold tabular text-text">{value}</div>
    </div>
  );
}
