"use client";

import { Network, Timeline, ShieldCheck } from "lucide-react";
import Link from "next/link";

export function InvestigationContextRail({
  tenderCount,
  relationshipCount,
  datedEventCount,
  riskSignalCount
}: {
  tenderCount: number;
  relationshipCount: number;
  datedEventCount: number;
  riskSignalCount: number;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <ContextLink href="/tenders" icon={<Timeline className="h-4 w-4" />} label="Records" value={tenderCount} detail="tenders in scope" />
      <ContextLink href="/graph" icon={<Network className="h-4 w-4" />} label="Network" value={relationshipCount} detail="relationships available" />
      <ContextLink href="/timeline" icon={<Timeline className="h-4 w-4" />} label="Chronology" value={datedEventCount} detail="dated events" />
      <ContextLink href="/risk" icon={<ShieldCheck className="h-4 w-4" />} label="Review signals" value={riskSignalCount} detail="signals to assess" />
    </div>
  );
}

function ContextLink({
  href,
  icon,
  label,
  value,
  detail
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  value: number;
  detail: string;
}) {
  return (
    <Link href={href} className="group rounded-xl border border-border bg-surface/60 p-3 transition-colors hover:border-border-strong hover:bg-surface">
      <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
        <span className="text-accent">{icon}</span>{label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular text-text">{value.toLocaleString("en-IN")}</div>
      <div className="mt-0.5 text-[10.5px] text-faint">{detail}</div>
    </Link>
  );
}
