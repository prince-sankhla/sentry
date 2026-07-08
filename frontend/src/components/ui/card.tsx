import type { ReactNode } from "react";
import { AnimatedValue } from "@/components/ui/animated-value";

export function SurfaceCard({
  children,
  className = ""
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`overflow-hidden rounded-[18px] border border-border bg-surface elevate ${className}`}
    >
      {children}
    </section>
  );
}

export function Section({
  action,
  children,
  eyebrow,
  title
}: {
  action?: ReactNode;
  children: ReactNode;
  eyebrow?: string;
  title: string;
}) {
  return (
    <SurfaceCard>
      <div className="flex items-center justify-between gap-4 border-b border-border bg-bg-2/40 px-5 py-3.5">
        <div className="min-w-0">
          {eyebrow ? (
            <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">
              <span className="h-1 w-1 rounded-full bg-accent/70" />
              {eyebrow}
            </div>
          ) : null}
          <h2 className="truncate text-sm font-semibold text-text">{title}</h2>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </SurfaceCard>
  );
}

const STAT_TONES = {
  neutral: { ring: "border-border", accent: "text-muted", bar: "bg-border-strong" },
  accent: { ring: "border-accent/40", accent: "text-accent", bar: "bg-accent" },
  success: { ring: "border-success/40", accent: "text-success", bar: "bg-success" },
  warning: { ring: "border-warning/40", accent: "text-warning", bar: "bg-warning" },
  danger: { ring: "border-danger/40", accent: "text-danger", bar: "bg-danger" }
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
      className={`group relative overflow-hidden rounded-[16px] border ${t.ring} bg-surface p-4 elevate transition duration-200 hover:-translate-y-0.5 hover:border-border-strong`}
    >
      <span className={`absolute inset-x-0 top-0 h-px ${t.bar} opacity-60`} />
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">
          {label}
        </div>
        {icon ? <span className={t.accent}>{icon}</span> : null}
      </div>
      <AnimatedValue
        value={value}
        className="mt-3 block break-words text-[28px] font-semibold leading-none tabular text-text"
      />
      {meta ? <div className="mt-2 text-xs text-muted">{meta}</div> : null}
    </div>
  );
}
