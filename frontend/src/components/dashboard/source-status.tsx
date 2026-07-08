"use client";

import { CheckCircle2, Circle } from "lucide-react";
import { bySourcePriority, sourceMeta } from "@/lib/sources";
import { formatNumber } from "@/lib/format";

/**
 * Data-source health list — Indian procurement sources first (GeM, CPPP, NIC),
 * World Bank and other international feeds shown as supplementary below.
 */
export function SourceStatus({ sources }: { sources: { source_name: string; tenders: number }[] }) {
  const ordered = bySourcePriority(sources, (s) => s.source_name);

  if (ordered.length === 0) {
    return <p className="text-sm text-faint">No sources connected.</p>;
  }

  return (
    <ul className="space-y-1.5">
      {ordered.map((s) => {
        const meta = sourceMeta(s.source_name);
        const live = s.tenders > 0;
        return (
          <li key={s.source_name} className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 transition hover:bg-surface-2">
            <span className="flex min-w-0 items-center gap-2.5">
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-md border ${meta.indian ? "border-accent/30 bg-accent/10 text-accent" : "border-border bg-bg-2 text-muted"}`}>
                {live ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm text-text">{meta.label}</span>
                <span className="block text-[11px] text-faint">{formatNumber(s.tenders)} tenders</span>
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-1.5">
              {meta.indian && <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">India</span>}
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${live ? "bg-success/10 text-success" : "bg-surface-2 text-faint"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-success pulse-live" : "bg-faint"}`} />
                {live ? "Live" : "Idle"}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
