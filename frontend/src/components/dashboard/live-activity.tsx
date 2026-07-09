"use client";

import { motion } from "framer-motion";
import { Activity, Award, FileText, Flag, Building2 } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import type { DashboardRecent, TimelineEvent } from "@/lib/api";
import { formatCompactMoney, formatDate } from "@/lib/format";

type FeedItem = {
  id: string;
  icon: typeof FileText;
  tone: string;
  dot: string;
  label: string;
  title: string;
  subtitle: string;
  href: string | null;
  when: string;
};

/**
 * Live activity feed — merges the analytics timeline (tender publications,
 * closings, awards) with recent imports into one chronological rail.
 */
export function LiveActivityFeed({
  timeline,
  recent
}: {
  timeline: TimelineEvent[];
  recent: DashboardRecent;
}) {
  const items = useMemo<FeedItem[]>(() => {
    const fromTimeline: FeedItem[] = timeline.slice(0, 8).map((e, i) => ({
      id: `tl-${i}`,
      icon: e.kind === "award" ? Award : e.kind === "tender_closing" ? Flag : FileText,
      tone: e.kind === "award" ? "text-success" : e.kind === "tender_closing" ? "text-warning" : "text-info",
      dot: e.kind === "award" ? "bg-success" : e.kind === "tender_closing" ? "bg-warning" : "bg-info",
      label: e.kind === "award" ? "Award" : e.kind === "tender_closing" ? "Closing" : "Published",
      title: e.title,
      subtitle: e.subtitle ?? (e.kind === "award" ? "Contract awarded" : "Tender published"),
      href: e.entity_type === "tender" && e.entity_id ? `/tenders/${e.entity_id}` : e.entity_type === "company" && e.entity_id ? `/companies/${e.entity_id}` : null,
      when: formatDate(e.date)
    }));

    const fromCompanies: FeedItem[] = recent.latest_awarded_companies.slice(0, 2).map((c) => ({
      id: `co-${c.id}`,
      icon: Building2,
      tone: "text-accent",
      dot: "bg-accent",
      label: "Supplier",
      title: c.name,
      subtitle: "New supplier onboarded",
      href: `/companies/${c.id}`,
      when: formatDate(c.created_at)
    }));

    return [...fromTimeline, ...fromCompanies].slice(0, 9);
  }, [timeline, recent]);

  if (items.length === 0) {
    return <p className="text-sm text-faint">No recent activity.</p>;
  }

  const awardCount = items.filter((item) => item.label === "Award").length;
  const closingCount = items.filter((item) => item.label === "Closing").length;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <ActivityMetric label="Events" value={String(items.length)} tone="text-accent" />
        <ActivityMetric label="Awards" value={String(awardCount)} tone="text-success" />
        <ActivityMetric label="Closings" value={String(closingCount)} tone="text-warning" />
      </div>

      <ul className="relative space-y-1">
        <span className="absolute bottom-4 left-[19px] top-4 w-px bg-border" aria-hidden />
        {items.map((item, i) => {
          const Icon = item.icon;
          const body = (
            <motion.div
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03, duration: 0.2 }}
              className="relative flex items-start gap-3 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2"
            >
              <span className={`relative z-10 mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md border border-border bg-bg-2 ${item.tone}`}>
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="mb-1 inline-flex items-center gap-1 rounded border border-border bg-bg-2/60 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-faint">
                  <span className={`h-1.5 w-1.5 rounded-full ${item.dot}`} />
                  {item.label}
                </span>
                <span className="block truncate text-sm text-text">{item.title}</span>
                <span className="block truncate text-xs text-faint">{item.subtitle}</span>
              </span>
              <span className="shrink-0 pt-0.5 text-[11px] text-faint">{item.when}</span>
            </motion.div>
          );
          return <li key={item.id}>{item.href ? <Link href={item.href}>{body}</Link> : body}</li>;
        })}
      </ul>
    </div>
  );
}

function ActivityMetric({
  label,
  value,
  tone
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-2/40 p-2.5">
      <Activity className={`h-3.5 w-3.5 ${tone}`} />
      <div className={`mt-1 tabular text-sm font-semibold ${tone}`}>{value}</div>
      <div className="text-[9px] font-semibold uppercase tracking-wide text-faint">{label}</div>
    </div>
  );
}
