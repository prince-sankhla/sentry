import type { ReactNode } from "react";

/**
 * Status chips.
 *
 * Every chip here encodes *state*, never brand. That is why none of the risk
 * tones are emerald: on this platform emerald means "this is the action to
 * take", and a severity badge must never borrow that signal.
 *
 * The risk lattice is ordinal — low → medium → high → critical — and is the
 * same ramp the graph, charts and map use (`lib/theme.ts`).
 */

/* ---------------------------------------------------------------- risk chip */

export type RiskLevel =
  | "low"
  | "medium"
  | "high"
  | "critical"
  | "insufficient";

const RISK_TONES: Record<RiskLevel, { cls: string; label: string }> = {
  low: {
    cls: "border-risk-low/40 bg-risk-low/10 text-risk-low",
    label: "Low"
  },
  medium: {
    cls: "border-risk-med/40 bg-risk-med/10 text-risk-med",
    label: "Medium"
  },
  high: {
    cls: "border-risk-high/40 bg-risk-high/10 text-risk-high",
    label: "High"
  },
  critical: {
    cls: "border-risk-crit/50 bg-risk-crit/15 text-risk-crit",
    label: "Critical"
  },
  insufficient: {
    cls: "border-border bg-surface-2 text-faint",
    label: "Insufficient evidence"
  }
};

/** Normalises the varied level strings the risk engine emits. */
export function riskLevel(value: string | null | undefined): RiskLevel {
  const v = (value ?? "").toLowerCase().trim();
  if (v.startsWith("crit")) return "critical";
  if (v.startsWith("high")) return "high";
  if (v.startsWith("med") || v.startsWith("mod")) return "medium";
  if (v.startsWith("low")) return "low";
  return "insufficient";
}

export function RiskChip({
  level,
  score,
  label,
  size = "md"
}: {
  level: RiskLevel | string;
  score?: number;
  /** Overrides the default level label. */
  label?: string;
  size?: "sm" | "md";
}) {
  const key = (
    level in RISK_TONES ? level : riskLevel(String(level))
  ) as RiskLevel;
  const tone = RISK_TONES[key];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-[0.08em] ${
        tone.cls
      } ${size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]"}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label ?? tone.label}
      {typeof score === "number" && (
        <span className="tabular font-medium opacity-80">· {score}</span>
      )}
    </span>
  );
}

/* --------------------------------------------------------------- state chip */

export type ChipTone =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "outline";

const CHIP_TONES: Record<ChipTone, string> = {
  neutral: "border-border bg-surface-2 text-muted",
  /* emerald — reserved for brand-adjacent affirmations, not status */
  accent: "border-accent/30 bg-accent/10 text-accent",
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-warning",
  danger: "border-danger/30 bg-danger/10 text-danger",
  info: "border-info/30 bg-info/10 text-info",
  outline: "border-border bg-transparent text-faint"
};

export function Chip({
  children,
  tone = "neutral",
  icon,
  className = ""
}: {
  children: ReactNode;
  tone?: ChipTone;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-[11px] font-medium ${CHIP_TONES[tone]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
}

/* --------------------------------------------------------------- live chip */

/**
 * Pulsing status dot with a label — system health, live feeds, running jobs.
 * `pulse` should be reserved for genuinely live state.
 */
export function StatusChip({
  label,
  tone = "success",
  detail,
  pulse = false
}: {
  label: string;
  tone?: "success" | "warning" | "danger" | "neutral";
  detail?: string;
  pulse?: boolean;
}) {
  const dot = {
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-danger",
    neutral: "bg-faint"
  }[tone];

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-[11px] font-medium text-muted">
      <span className="relative flex h-1.5 w-1.5">
        {pulse && (
          <span
            className={`absolute inline-flex h-full w-full rounded-full ${dot} pulse-live`}
          />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${dot}`} />
      </span>
      <span className="text-text">{label}</span>
      {detail && (
        <>
          <span className="text-faint">·</span>
          <span>{detail}</span>
        </>
      )}
    </span>
  );
}

/* -------------------------------------------------------------- count chip */

/** Small tabular counter used beside tab labels and section titles. */
export function CountChip({ value }: { value: number | string }) {
  return (
    <span className="tabular inline-flex min-w-[20px] items-center justify-center rounded-md border border-border bg-bg-2 px-1.5 py-0.5 text-[10.5px] font-semibold text-muted">
      {value}
    </span>
  );
}
