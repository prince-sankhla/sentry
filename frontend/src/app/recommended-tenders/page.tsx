import Link from "next/link";
import { ArrowRight, CheckCircle2, ListChecks } from "lucide-react";

import { getPriorityQueue, type PriorityQueueItem } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatNumber } from "@/lib/format";

type RecommendedTender = PriorityQueueItem & {
  tender_id?: string | null;
  reference_number?: string | null;
  tender_title?: string | null;
};

export const dynamic = "force-dynamic";

export default async function RecommendedTendersPage() {
  let items: RecommendedTender[] = [];
  try {
    const response = await getPriorityQueue(100);
    items = response.items.filter((item) => item.investigation_type === "tender") as RecommendedTender[];
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Lead Discovery" title="Recommended Tenders" subtitle="Deterministic tender leads SENTRY recommends opening first." />
        <ErrorState title="Recommended tender queue unavailable" message="SENTRY could not load the current recommendation queue." />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="Lead Discovery"
        title="Recommended Tenders"
        subtitle="This queue contains tender-level leads surfaced by the deterministic investigation engine. Recommendation explains where to start; it is not an adjudication."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3">
        <Stat label="Recommended tenders" value={formatNumber(items.length)} />
        <Stat label="With multiple typologies" value={formatNumber(items.filter((item) => item.typology_count > 1).length)} />
        <Stat label="High evidence" value={formatNumber(items.filter((item) => item.evidence_strength === "high").length)} />
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={<ListChecks className="h-5 w-5" />}
          title="No recommended tender leads"
          message="The current procurement database does not expose a tender-level recommendation lead."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((item, index) => {
            const target = item.reference_number ?? item.tender_id ?? item.subject;
            const href = item.tender_id ? "/tenders/" + item.tender_id : "/investigate?q=" + encodeURIComponent(target);
            return (
              <article key={(item.tender_id ?? item.subject) + "-" + index} className="group flex flex-col rounded-2xl border border-border bg-surface p-5 transition hover:border-accent/35">
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.13em] text-accent">
                    <CheckCircle2 className="h-3 w-3" /> Recommended lead
                  </span>
                  <span className="text-[11px] text-faint">Evidence: <span className="font-semibold text-text">{item.evidence_strength}</span></span>
                </div>

                <div className="mt-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Tender</div>
                  <h2 className="mt-1 text-[16px] font-semibold leading-6 text-text group-hover:text-accent">{item.subject}</h2>
                  {item.reference_number ? <div className="mt-1 font-mono text-xs text-faint">{item.reference_number}</div> : null}
                </div>

                <div className="mt-4 rounded-xl border border-border bg-bg-2/40 p-3.5">
                  <div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">Why SENTRY recommends this lead</div>
                  <ul className="mt-2 space-y-2">
                    {item.reasons.map((reason) => (
                      <li key={reason} className="flex items-start gap-2 text-xs leading-5 text-muted">
                        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-faint">
                  <span className="rounded-md border border-border bg-bg-2 px-2 py-1">{item.typology_count} typologies</span>
                  <span className="rounded-md border border-border bg-bg-2 px-2 py-1">{item.linked_records} linked records</span>
                  <span className="rounded-md border border-border bg-bg-2 px-2 py-1">Priority {item.priority}</span>
                </div>

                <div className="mt-auto pt-5">
                  <Link href={href} className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent">
                    Open tender <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                  </Link>
                </div>
              </article>
            );
          })}
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
