import { CalendarClock } from "lucide-react";
import { getAnalyticsTimeline } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { TimelineView } from "./timeline-view";

export const dynamic = "force-dynamic";

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
  const groups = new Map<string, (typeof data.events)[number][]>();
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
        <EmptyState
          icon={<CalendarClock className="h-5 w-5" />}
          title="No dated events"
          message="No tenders or awards carry dates yet. Import procurement data to populate the timeline."
        />
      ) : (
        <TimelineView groups={[...groups.entries()]} />
      )}
    </PageShell>
  );
}
