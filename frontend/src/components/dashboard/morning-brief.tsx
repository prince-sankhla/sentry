"use client";

/**
 * Morning Intelligence Brief — the Command Center hero.
 *
 * Reads like the top of an analyst's daily briefing: a dateline, a one-glance
 * "state of the board" headline synthesised from live totals + risk, three
 * priority read-outs (activity / attention / direction), and a single primary
 * action to open an investigation. No decoration that doesn't carry meaning.
 */

import { motion } from "framer-motion";
import { ArrowUpRight, Radar, Sparkles, TrendingUp, Zap } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { AnalyticsOverview, RiskResponse, TimelineResponse } from "@/lib/api";
import { AnimatedValue } from "@/components/ui/animated-value";
import { formatCompactMoney, formatNumber } from "@/lib/format";

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

function dateline(): string {
  // Rendered client-side only, so a live clock is safe here.
  const d = new Date();
  return `${WEEKDAYS[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function MorningBrief({
  overview,
  risk,
  timeline,
  onLaunch
}: {
  overview: AnalyticsOverview;
  risk: RiskResponse;
  timeline: TimelineResponse;
  onLaunch: (q: string) => void;
}) {
  const [q, setQ] = useState("");
  const t = overview.totals;

  const todayEvents = timeline.events.length;
  const highRisk = risk.summary.high;
  const topSignal = risk.signals[0];

  const headline = useMemo(() => {
    if (highRisk > 0) {
      return (
        <>
          <span className="text-danger">{highRisk} high-risk {highRisk === 1 ? "signal" : "signals"}</span>{" "}
          require review across{" "}
          <span className="text-text">{formatNumber(t.tenders)}</span> tracked tenders.
        </>
      );
    }
    return (
      <>
        Procurement across <span className="text-text">{formatNumber(t.buyers)}</span> buyers is nominal —
        no high-risk signals outstanding.
      </>
    );
  }, [highRisk, t.tenders, t.buyers]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="relative overflow-hidden rounded-[22px] border border-border bg-surface/80 elevate"
    >
      {/* ambient copper dawn — meaning: "start of day / brief" */}
      <div className="pointer-events-none absolute -right-24 -top-28 h-72 w-72 rounded-full bg-accent/[0.07] blur-3xl" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />

      <div className="relative grid gap-6 p-6 md:p-8 lg:grid-cols-[1.5fr_1fr]">
        {/* left: the brief */}
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
            <Sparkles className="h-3.5 w-3.5" />
            Morning Intelligence Brief
          </div>
          <div className="mt-1 text-xs text-faint">{dateline()} · India Procurement</div>

          <h1 className="mt-4 text-[22px] font-semibold leading-snug tracking-tight text-muted md:text-[26px]">
            {headline}
          </h1>

          {topSignal && (
            <div className="mt-4 flex items-start gap-2.5 rounded-[14px] border border-border bg-bg-2/50 p-3.5">
              <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md border border-danger/30 bg-danger/10 text-danger">
                <Radar className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-faint">Top priority</div>
                <div className="mt-0.5 truncate text-sm font-medium text-text">{topSignal.title}</div>
                <div className="line-clamp-1 text-xs text-muted">{topSignal.summary}</div>
              </div>
            </div>
          )}

          {/* launcher */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (q.trim()) onLaunch(q.trim());
            }}
            className="mt-5 flex flex-col gap-2 sm:flex-row"
          >
            <div className="relative flex-1">
              <Zap className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-accent" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Investigate an entity, buyer, or pattern…"
                className="h-11 w-full rounded-xl border border-border bg-bg/60 pl-10 pr-4 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/60"
              />
            </div>
            <button
              type="submit"
              className="flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-accent px-5 text-sm font-semibold text-bg transition hover:bg-accent-hi"
            >
              Launch investigation
              <ArrowUpRight className="h-4 w-4" />
            </button>
          </form>
        </div>

        {/* right: three priority read-outs */}
        <div className="grid grid-cols-3 gap-3 lg:grid-cols-1">
          <BriefStat
            label="Activity today"
            value={formatNumber(todayEvents)}
            sub="events on the wire"
            tone="info"
            icon={<TrendingUp className="h-4 w-4" />}
          />
          <BriefStat
            label="Needs attention"
            value={formatNumber(highRisk)}
            sub="high-risk signals"
            tone={highRisk > 0 ? "danger" : "success"}
            icon={<Radar className="h-4 w-4" />}
          />
          <BriefStat
            label="Awarded value"
            value={formatCompactMoney(t.total_awarded_value)}
            sub="tracked contracts"
            tone="accent"
            icon={<ArrowUpRight className="h-4 w-4" />}
          />
        </div>
      </div>
    </motion.section>
  );
}

const STAT_TONE = {
  accent: "text-accent",
  info: "text-info",
  danger: "text-danger",
  success: "text-success"
} as const;

function BriefStat({
  label,
  value,
  sub,
  tone,
  icon
}: {
  label: string;
  value: string;
  sub: string;
  tone: keyof typeof STAT_TONE;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-[14px] border border-border bg-bg-2/50 p-3.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{label}</span>
        <span className={STAT_TONE[tone]}>{icon}</span>
      </div>
      <AnimatedValue value={value} className={`mt-2 block text-2xl font-semibold tabular ${STAT_TONE[tone]}`} />
      <div className="mt-0.5 text-[11px] text-faint">{sub}</div>
    </div>
  );
}
