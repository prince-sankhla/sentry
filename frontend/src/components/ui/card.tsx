import type { ReactNode } from "react";
import { AnimatedValue } from "@/components/ui/animated-value";

/**
 * Card surfaces.
 *
 * `SurfaceCard` is the plain shell; `Section` adds the standard header rail.
 * Both sit on the same hairline + radius as `Panel`, so a page mixing them
 * reads as one system.
 */

export function SurfaceCard({
  children,
  className = ""
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`overflow-hidden rounded-2xl border border-border bg-surface elevate transition-colors duration-200 ${className}`}
    >
      {children}
    </section>
  );
}

export function Section({
  action,
  children,
  eyebrow,
  title,
  className = ""
}: {
  action?: ReactNode;
  children: ReactNode;
  eyebrow?: string;
  title: string;
  className?: string;
}) {
  return (
    <SurfaceCard className={className}>
      <div className="flex items-center justify-between gap-4 border-b border-border bg-bg-2/40 px-6 py-4">
        <div className="min-w-0">
          {eyebrow ? (
            <div className="mb-1 flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-accent/70" />
              <span className="t-label">{eyebrow}</span>
            </div>
          ) : null}
          <h2 className="truncate text-[15px] font-semibold tracking-[-0.014em] text-text">
            {title}
          </h2>
        </div>
        {action}
      </div>
      <div className="p-6">{children}</div>
    </SurfaceCard>
  );
}

/**
 * Compact statistic tile.
 *
 * `accent` is available but should be spent on the single most important
 * figure on a screen — status figures belong on `success`/`warning`/`danger`,
 * which read as state rather than as a call to action.
 */
const STAT_TONES = {
  neutral: { ring: "border-border", accent: "text-muted", bar: "bg-border-strong" },
  accent: { ring: "border-accent/35", accent: "text-accent", bar: "bg-accent" },
  success: { ring: "border-success/35", accent: "text-success", bar: "bg-success" },
  warning: { ring: "border-warning/35", accent: "text-warning", bar: "bg-warning" },
  danger: { ring: "border-danger/35", accent: "text-danger", bar: "bg-danger" }
} as const;

export function StatCard({
  label,
  tone = "neutral",
  value,
  meta,
  icon
}: {
  label: string;
  tone?: keyof typeof STAT_TONES;
  value: string;
  meta?: string;
  icon?: ReactNode;
}) {
  const t = STAT_TONES[tone];
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border ${t.ring} bg-surface p-5 elevate transition-all duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] hover:-translate-y-0.5 hover:border-border-strong`}
    >
      <span className={`absolute inset-x-0 top-0 h-px ${t.bar} opacity-50`} />
      <div className="flex items-center justify-between">
        <div className="t-label">{label}</div>
        {icon ? <span className={t.accent}>{icon}</span> : null}
      </div>
      <AnimatedValue
        value={value}
        className="mt-4 block break-words text-[30px] font-semibold leading-none tracking-[-0.024em] tabular text-text"
      />
      {meta ? <div className="mt-2.5 text-[13px] text-muted">{meta}</div> : null}
    </div>
  );
}
