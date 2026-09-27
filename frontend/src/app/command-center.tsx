"use client";

import {
  Activity,
  Award,
  Building2,
  CheckCircle2,
  FileText,
  Flag,
  Landmark,
  RadioTower,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Section } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { SeverityBadge } from "@/components/ui/page";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { RoleCommandCenter } from "@/components/dashboard/role-command-center";
import { SourceStatus } from "@/components/dashboard/source-status";
import {
  getAnalyticsOverview,
  getRisk,
  type AnalyticsOverview,
  type RiskResponse,
} from "@/lib/api";
import { formatCompactMoney, formatNumber } from "@/lib/format";

type Bundle = {
  overview: AnalyticsOverview;
  risk: RiskResponse;
};

export function CommandCenter() {
  const router = useRouter();
  const [data, setData] = useState<Bundle | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    Promise.all([getAnalyticsOverview(), getRisk()])
      .then(([overview, risk]) => setData({ overview, risk }))
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="mt-6">
        <ErrorState message="SENTRY could not load the command center. Check the data connection and retry." />
      </div>
    );
  }

  if (!data) return <CommandCenterSkeleton />;

  return (
    <CommandCenterView
      data={data}
      onLaunch={(query) =>
        router.push("/investigate?q=" + encodeURIComponent(query))
      }
    />
  );
}

function CommandCenterView({
  data,
  onLaunch,
}: {
  data: Bundle;
  onLaunch: (query: string) => void;
}) {
  const { overview, risk } = data;
  const totals = overview.totals;
  const attention = risk.summary.high + risk.summary.medium;

  return (
    <div className="space-y-5">
      <div className="overflow-hidden rounded-2xl border border-border bg-surface elevate">
        <div className="px-6 py-7">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-accent/25 bg-accent/[.07] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.14em] text-accent">
                <span className="h-1.5 w-1.5 rounded-full bg-accent pulse-live" />
                Live intelligence
              </div>
              <h1 className="text-[28px] font-semibold tracking-[-.035em] text-text sm:text-[34px]">
                Procurement intelligence, built for investigation.
              </h1>
              <p className="mt-2.5 text-sm leading-6 text-muted">
                Start from a clean work queue, open the exact tender surface you
                need, then follow evidence into investigation.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <QuickStat label="Review signals" value={formatNumber(risk.summary.total)} />
              <QuickStat label="Need review" value={formatNumber(attention)} />
              <QuickStat label="High severity" value={formatNumber(risk.summary.high)} />
              <QuickStat label="Sources" value={formatNumber(overview.sources.length)} />
            </div>
          </div>
        </div>

        <div className="grid border-t border-border bg-bg-2/30 sm:grid-cols-2 xl:grid-cols-4">
          <ActionLink
            href="/flagged-tenders"
            icon={<ShieldAlert className="h-4 w-4" />}
            title="Flagged tenders"
            detail="Tender-linked review signals"
          />
          <ActionLink
            href="/recommended-tenders"
            icon={<CheckCircle2 className="h-4 w-4" />}
            title="Recommended tenders"
            detail="Deterministic lead queue"
          />
          <ActionLink
            href="/field"
            icon={<RadioTower className="h-4 w-4" />}
            title="Physical verification"
            detail="FIELD-ready tender leads"
          />
          <ActionLink
            href="/tenders"
            icon={<FileText className="h-4 w-4" />}
            title="All tenders"
            detail="Complete procurement record list"
          />
        </div>
      </div>

      <RoleCommandCenter />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard
          href="/tenders"
          label="Tenders"
          value={formatNumber(totals.tenders)}
          tone="accent"
          icon={<FileText className="h-4 w-4" />}
        />
        <KpiCard
          href="/awards"
          label="Awarded value"
          value={formatCompactMoney(totals.total_awarded_value)}
          tone="success"
          icon={<Award className="h-4 w-4" />}
        />
        <KpiCard
          href="/buyers"
          label="Buyers"
          value={formatNumber(totals.buyers)}
          tone="info"
          icon={<Landmark className="h-4 w-4" />}
        />
        <KpiCard
          href="/companies"
          label="Suppliers"
          value={formatNumber(totals.companies)}
          icon={<Building2 className="h-4 w-4" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Section
          eyebrow="Review snapshot"
          title={formatNumber(attention) + " signals currently need review"}
          action={
            <Link
              href="/flagged-tenders"
              className="text-xs font-medium text-accent"
            >
              Open flagged tenders →
            </Link>
          }
        >
          {risk.signals.length ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {risk.signals.slice(0, 6).map((signal, index) => (
                <Link
                  key={signal.title + "-" + index}
                  href={
                    signal.tender_id
                      ? "/tenders/" + signal.tender_id
                      : "/risk"
                  }
                  className="rounded-xl border border-border bg-bg-2/40 p-3 hover:border-border-strong"
                >
                  <div className="flex items-start gap-2">
                    <Flag className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[12px] font-medium text-text">
                        {signal.title}
                      </div>
                      <div className="mt-0.5 line-clamp-2 text-[11px] text-faint">
                        {signal.buyer ?? signal.supplier_name ?? signal.summary}
                      </div>
                    </div>
                    <SeverityBadge
                      severity={signal.severity}
                      score={signal.score}
                    />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No active review signals"
              message="No screening signal currently falls within the selected scope."
            />
          )}
        </Section>

        <Section eyebrow="Sources" title="Data source status">
          <SourceStatus sources={overview.sources} />
        </Section>
      </div>

      <Section
        eyebrow="Start investigation"
        title="Investigate a procurement subject"
      >
        <button
          onClick={() => onLaunch("Recent Indian procurement")}
          className="rounded-xl border border-accent/25 bg-accent/[.06] px-4 py-3 text-sm font-medium text-accent hover:bg-accent/10"
        >
          Open investigation workspace →
        </button>
      </Section>
    </div>
  );
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg-2/50 px-3.5 py-3">
      <div className="text-[9px] font-semibold uppercase tracking-[.12em] text-faint">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular text-text">
        {value}
      </div>
    </div>
  );
}

function ActionLink({
  href,
  icon,
  title,
  detail,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 border-r border-border p-4 transition hover:bg-surface-2 last:border-r-0"
    >
      <span className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-accent">
        {icon}
      </span>
      <span>
        <span className="block text-sm font-medium text-text">{title}</span>
        <span className="mt-0.5 block text-xs text-faint">{detail}</span>
      </span>
    </Link>
  );
}

function CommandCenterSkeleton() {
  return (
    <div className="mt-6 space-y-4">
      {[1, 2, 3].map((item) => (
        <div
          key={item}
          className="h-28 animate-pulse rounded-2xl border border-border bg-surface"
        />
      ))}
    </div>
  );
}
