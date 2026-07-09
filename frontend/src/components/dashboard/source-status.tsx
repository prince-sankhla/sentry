"use client";

import { CheckCircle2, Circle, Database, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { bySourcePriority, sourceMeta } from "@/lib/sources";
import { formatNumber } from "@/lib/format";

/**
 * Data-source health list — Indian procurement sources first (GeM, CPPP, NIC),
 * World Bank and other international feeds shown as supplementary below.
 */
export function SourceStatus({ sources }: { sources: { source_name: string; tenders: number }[] }) {
  const ordered = bySourcePriority(sources, (s) => s.source_name);
  const total = ordered.reduce((sum, s) => sum + s.tenders, 0);
  const active = ordered.filter((s) => s.tenders > 0).length;
  const indian = ordered.filter((s) => sourceMeta(s.source_name).indian && s.tenders > 0).length;
  const max = Math.max(1, ...ordered.map((s) => s.tenders));

  if (ordered.length === 0) {
    return <p className="text-sm text-faint">No sources connected.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <SourceMetric icon={<ShieldCheck className="h-3.5 w-3.5" />} label="Active" value={`${active}/${ordered.length}`} />
        <SourceMetric icon={<Database className="h-3.5 w-3.5" />} label="Records" value={formatNumber(total)} />
        <SourceMetric icon={<CheckCircle2 className="h-3.5 w-3.5" />} label="India" value={String(indian)} />
      </div>

      <ul className="space-y-1.5">
        {ordered.map((s) => {
          const meta = sourceMeta(s.source_name);
          const live = s.tenders > 0;
          const pct = Math.max(live ? 4 : 0, Math.round((s.tenders / max) * 100));
          return (
            <li
              key={s.source_name}
              className="rounded-lg border border-transparent px-2 py-2 transition hover:border-border hover:bg-surface-2"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="flex min-w-0 items-center gap-2.5">
                  <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-md border ${meta.indian ? "border-accent/30 bg-accent/10 text-accent" : "border-border bg-bg-2 text-muted"}`}>
                    {live ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-text">{meta.label}</span>
                    <span className="block text-[11px] text-faint">{formatNumber(s.tenders)} tenders indexed</span>
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1.5">
                  {meta.indian && <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">India</span>}
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${live ? "bg-success/10 text-success" : "bg-surface-2 text-faint"}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-success pulse-live" : "bg-faint"}`} />
                    {live ? "Live" : "Idle"}
                  </span>
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg">
                <div
                  className={`h-full rounded-full ${meta.indian ? "bg-accent/75" : "bg-info/65"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SourceMetric({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-2/40 p-2.5">
      <div className="flex items-center justify-between text-accent">{icon}</div>
      <div className="mt-1 tabular text-sm font-semibold text-text">{value}</div>
      <div className="text-[9px] font-semibold uppercase tracking-wide text-faint">{label}</div>
    </div>
  );
}
