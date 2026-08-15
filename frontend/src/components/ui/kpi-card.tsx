"use client";

import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { Sparkline } from "@/components/charts";
import { AnimatedValue } from "@/components/ui/animated-value";
import { CHART, PALETTE, alpha } from "@/lib/theme";
import { SPRING_SOFT } from "@/lib/motion";

/**
 * Flagship KPI card — icon chip, micro-label, large tabular value, delta pill
 * against the previous period, and an embedded sparkline.
 *
 * The delta pill is the one place green and red appear together; it uses the
 * semantic pair rather than the brand accent, so "up" never reads as "click me".
 */
const TONES = {
  accent: {
    icon: "text-accent",
    ring: "border-accent/25",
    glow: alpha(PALETTE.accent, 0.1),
    spark: CHART.accent
  },
  info: {
    icon: "text-info",
    ring: "border-info/25",
    glow: alpha(PALETTE.info, 0.1),
    spark: CHART.info
  },
  success: {
    icon: "text-success",
    ring: "border-success/25",
    glow: alpha(PALETTE.success, 0.1),
    spark: CHART.success
  },
  danger: {
    icon: "text-danger",
    ring: "border-danger/25",
    glow: alpha(PALETTE.danger, 0.1),
    spark: CHART.danger
  },
  neutral: {
    icon: "text-muted",
    ring: "border-border",
    glow: alpha(PALETTE.muted, 0.07),
    spark: CHART.text
  }
} as const;

export function KpiCard({
  label,
  value,
  icon,
  tone = "neutral",
  delta,
  deltaLabel = "vs last 30 days",
  spark,
  href
}: {
  label: string;
  value: string;
  icon?: ReactNode;
  tone?: keyof typeof TONES;
  delta?: number;
  deltaLabel?: string;
  spark?: number[];
  href?: string;
}) {
  const t = TONES[tone];
  const up = (delta ?? 0) >= 0;

  const inner = (
    <motion.div
      whileHover={{ y: -3 }}
      transition={SPRING_SOFT}
      className={`group relative overflow-hidden rounded-2xl border ${t.ring} bg-surface p-5 elevate transition-colors duration-200 hover:border-border-strong`}
    >
      <div
        className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full opacity-60 blur-2xl transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: t.glow }}
        aria-hidden
      />
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          {icon && (
            <span
              className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 ${t.icon}`}
            >
              {icon}
            </span>
          )}
          <span className="t-label truncate">{label}</span>
        </div>
        {typeof delta === "number" && (
          <span
            className={`inline-flex shrink-0 items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular ${
              up ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
            }`}
          >
            {up ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <AnimatedValue
            value={value}
            className="block truncate text-[28px] font-semibold leading-none tracking-[-0.024em] tabular text-text"
          />
          {typeof delta === "number" && (
            <div className="mt-2 text-[11px] text-faint">{deltaLabel}</div>
          )}
        </div>
        {spark && spark.length > 1 && (
          <div className="h-10 w-24 shrink-0" aria-hidden>
            <Sparkline values={spark} color={t.spark} height={40} />
          </div>
        )}
      </div>
    </motion.div>
  );

  if (href) {
    return (
      <a href={href} className="block">
        {inner}
      </a>
    );
  }
  return inner;
}
