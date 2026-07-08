import { Award, CalendarClock, FileText, Flag } from "lucide-react";
import Link from "next/link";
import { getAnalyticsTimeline, type TimelineEvent } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

const KIND = {
  tender_published: { icon: FileText, tone: "text-info border-info/40 bg-info/10", label: "Tender published" },
  tender_closing: { icon: Flag, tone: "text-warning border-warning/40 bg-warning/10", label: "Tender closing" },
  award: { icon: Award, tone: "text-success border-success/40 bg-success/10", label: "Award" }
} as const;

function hrefFor(e: TimelineEvent): string | null {
  if (e.entity_type === "tender" && e.entity_id) return `/tenders/${e.entity_id}`;
  if (e.entity_type === "company" && e.entity_id) return `/companies/${e.entity_id}`;
  return null;
}

export default async function TimelinePage() {
  let data;
  try {
    data = await getAnalyticsTimeline(80);
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Analysis" title="Timeline" />
        <ErrorState message="Could not load the procurement timeline." />
      </PageShell>
    );
  }

  // group by day
  const groups = new Map<string, TimelineEvent[]>();
  for (const e of data.events) {
    const key = e.date.slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(e);
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="Analysis"
        title="Procurement Timeline"
        subtitle="Chronological feed of tender publications, closings, and contract awards across all sources."
      />

      {data.events.length === 0 ? (
        <EmptyState icon={<CalendarClock className="h-5 w-5" />} title="No dated events" message="No tenders or awards carry dates yet." />
      ) : (
        <div className="space-y-8">
          {[...groups.entries()].map(([day, events]) => (
            <div key={day} className="animate-rise">
              <div className="sticky top-16 z-10 mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-bg-2/90 px-3 py-1 text-xs font-medium text-muted backdrop-blur">
                <CalendarClock className="h-3.5 w-3.5 text-accent" />
                {formatDate(day)}
              </div>
              <div className="ml-1 space-y-2 border-l border-border pl-5">
                {events.map((e, i) => {
                  const meta = KIND[e.kind];
                  const Icon = meta.icon;
                  const href = hrefFor(e);
                  const body = (
                    <div className="relative rounded-[14px] border border-border bg-surface p-4 transition hover:border-border-strong">
                      <span
                        className={`absolute -left-[30px] top-4 grid h-6 w-6 place-items-center rounded-full border ${meta.tone}`}
                      >
                        <Icon className="h-3 w-3" />
                      </span>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">
                          {meta.label}
                        </span>
                        {e.reference && (
                          <span className="font-mono text-[11px] text-faint">{e.reference}</span>
                        )}
                      </div>
                      <div className="mt-1 text-sm font-medium text-text">{e.title}</div>
                      {e.subtitle && <div className="mt-0.5 text-xs text-muted">{e.subtitle}</div>}
                    </div>
                  );
                  return href ? (
                    <Link key={i} href={href} className="block">
                      {body}
                    </Link>
                  ) : (
                    <div key={i}>{body}</div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  );
}
