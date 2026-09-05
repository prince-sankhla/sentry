import { CalendarClock, Filter } from "lucide-react";
import Link from "next/link";
import { getAnalyticsTimeline } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { TimelineView } from "./timeline-view";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    kind?: string;
  }>;
};

const FILTERS = [
  { value: "all", label: "All events" },
  { value: "tender_published", label: "Published" },
  { value: "tender_closing", label: "Closing" },
  { value: "award", label: "Awards" }
] as const;

export default async function TimelinePage({ searchParams }: PageProps) {
  const params = await searchParams;
  let data;
  try {
    data = await getAnalyticsTimeline(160);
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Analysis" title="Timeline" />
        <ErrorState message="Could not load the procurement timeline." />
      </PageShell>
    );
  }

  const activeFilter = FILTERS.some((filter) => filter.value === params.kind) ? params.kind! : "all";
  const events = activeFilter === "all" ? data.events : data.events.filter((event) => event.kind === activeFilter);

  const groups = new Map<string, (typeof events)[number][]>();
  for (const e of events) {
    const key = e.date.slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(e);
  }

  const uniqueDays = groups.size;

  return (
    <PageShell>
      <PageHeader
        eyebrow="Analysis"
        title="Procurement Timeline"
        subtitle="Chronology for tender publications, closing dates and awards, with source-linked event details."
        actions={
          <div className="flex items-center gap-2 text-[11px] text-faint">
            <CalendarClock className="h-4 w-4 text-accent" />
            {uniqueDays.toLocaleString("en-IN")} days in view
          </div>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-surface/60 p-2">
        <span className="px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-faint"><Filter className="mr-1 inline h-3.5 w-3.5" />Event type</span>
        {FILTERS.map((filter) => (
          <Link
            key={filter.value}
            href={filter.value === "all" ? "/timeline" : `/timeline?kind=${filter.value}`}
            className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${activeFilter === filter.value ? "border-accent/45 bg-accent/10 text-accent" : "border-border bg-bg-2/50 text-muted hover:text-text"}`}
          >
            {filter.label}
          </Link>
        ))}
        <span className="ml-auto text-[10.5px] tabular text-faint">{events.length.toLocaleString("en-IN")} events</span>
      </div>

      {events.length === 0 ? (
        <EmptyState
          icon={<CalendarClock className="h-5 w-5" />}
          title="No events match this view"
          message="No tender or award events are available for the selected event type."
        />
      ) : (
        <TimelineView groups={[...groups.entries()]} />
      )}
    </PageShell>
  );
}
