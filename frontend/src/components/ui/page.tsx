import Link from "next/link";
import type { ReactNode } from "react";

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1500px] px-5 py-6 md:px-8 md:py-8">
      {children}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  breadcrumb
}: {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  breadcrumb?: { label: string; href?: string }[];
}) {
  return (
    <div className="mb-6 animate-rise">
      {breadcrumb && breadcrumb.length > 0 && (
        <nav className="mb-3 flex items-center gap-1.5 text-xs text-faint">
          {breadcrumb.map((c, i) => (
            <span key={`${c.label}-${i}`} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-border-strong">/</span>}
              {c.href ? (
                <Link href={c.href} className="transition hover:text-accent">
                  {c.label}
                </Link>
              ) : (
                <span className="text-muted">{c.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div className="min-w-0">
          {eyebrow && (
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
              {eyebrow}
            </div>
          )}
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-text md:text-[30px]">
            {title}
          </h1>
          {subtitle && (
            <div className="mt-1.5 max-w-2xl text-sm text-muted">{subtitle}</div>
          )}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className="rule mt-5" />
    </div>
  );
}

const SEVERITY = {
  high: "border-danger/40 bg-danger/10 text-danger",
  medium: "border-warning/40 bg-warning/10 text-warning",
  low: "border-success/40 bg-success/10 text-success"
} as const;

export function SeverityBadge({
  severity,
  score
}: {
  severity: "low" | "medium" | "high";
  score?: number;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${SEVERITY[severity]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {severity}
      {typeof score === "number" && (
        <span className="tabular opacity-80">· {score}</span>
      )}
    </span>
  );
}

export function Badge({
  children,
  tone = "neutral"
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "success" | "info" | "muted";
}) {
  const tones = {
    neutral: "border-border bg-surface-2 text-muted",
    accent: "border-accent/30 bg-accent/10 text-accent",
    success: "border-success/30 bg-success/10 text-success",
    info: "border-info/30 bg-info/10 text-info",
    muted: "border-border bg-transparent text-faint"
  } as const;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

/** Horizontal proportion bar used for rankings/distributions. */
export function RankBar({
  label,
  value,
  max,
  meta,
  href,
  tone = "accent"
}: {
  label: string;
  value: number;
  max: number;
  meta?: string;
  href?: string;
  tone?: "accent" | "info" | "success";
}) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  const bar = {
    accent: "bg-accent/70",
    info: "bg-info/70",
    success: "bg-success/70"
  }[tone];
  const inner = (
    <div className="group relative">
      <div className="mb-1 flex items-center justify-between gap-3 text-sm">
        <span className="truncate text-text">{label}</span>
        {meta && <span className="shrink-0 tabular text-xs text-muted">{meta}</span>}
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-2">
        <div
          className={`h-full rounded-full ${bar} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
  return href ? (
    <Link href={href} className="block transition hover:opacity-90">
      {inner}
    </Link>
  ) : (
    inner
  );
}
