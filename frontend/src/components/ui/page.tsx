import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Page scaffolding — the outer rhythm every route shares.
 *
 * `PageShell` sets the measure and the editorial gutter; `PageHeader` supplies
 * breadcrumb, display title and action rail. Between them they guarantee that
 * two unrelated screens still start at the same optical position.
 */

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1500px] px-6 py-8 md:px-10 md:py-12">
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
    <div className="mb-10 animate-rise">
      {breadcrumb && breadcrumb.length > 0 && (
        <nav
          aria-label="Breadcrumb"
          className="mb-4 flex flex-wrap items-center gap-1.5 text-[12px] text-faint"
        >
          {breadcrumb.map((c, i) => (
            <span key={`${c.label}-${i}`} className="flex items-center gap-1.5">
              {i > 0 && (
                <ChevronRight className="h-3 w-3 text-border-strong" aria-hidden />
              )}
              {c.href ? (
                <Link
                  href={c.href}
                  className="transition-colors duration-200 hover:text-accent"
                >
                  {c.label}
                </Link>
              ) : (
                <span className="text-muted">{c.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div className="min-w-0">
          {eyebrow && (
            <div className="mb-2.5 flex items-center gap-2">
              <span className="h-1 w-1 rounded-full bg-accent" />
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
                {eyebrow}
              </span>
            </div>
          )}
          <h1 className="text-[30px] font-semibold leading-[1.08] tracking-[-0.028em] text-text md:text-[38px]">
            {title}
          </h1>
          {subtitle && (
            <div className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">
              {subtitle}
            </div>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2.5">
            {actions}
          </div>
        )}
      </div>
      <div className="rule mt-8" />
    </div>
  );
}

/**
 * Severity badge.
 *
 * Kept on the risk lattice, not the brand accent — see `ui/chip.tsx` for the
 * reasoning. `RiskChip` is the fuller control; this stays for the three-level
 * call sites that already exist.
 */
const SEVERITY = {
  high: "border-risk-high/40 bg-risk-high/10 text-risk-high",
  medium: "border-risk-med/40 bg-risk-med/10 text-risk-med",
  low: "border-risk-low/40 bg-risk-low/10 text-risk-low"
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
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] ${SEVERITY[severity]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {severity}
      {typeof score === "number" && (
        <span className="tabular font-medium opacity-80">· {score}</span>
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
      className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}
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
      <div className="mb-2 flex items-center justify-between gap-3 text-[13px]">
        <span className="truncate text-text">{label}</span>
        {meta && (
          <span className="shrink-0 tabular text-xs text-muted">{meta}</span>
        )}
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-2">
        <div
          className={`h-full rounded-full ${bar} transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:opacity-100`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
  return href ? (
    <Link
      href={href}
      className="block transition-opacity duration-200 hover:opacity-90"
    >
      {inner}
    </Link>
  ) : (
    inner
  );
}
