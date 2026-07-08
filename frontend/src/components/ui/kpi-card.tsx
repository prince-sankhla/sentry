"use client";

import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { Sparkline } from "@/components/charts";
import { CHART } from "@/components/charts/echart";
import { AnimatedValue } from "@/components/ui/animated-value";

const TONES = {
  accent: { icon: "text-accent", ring: "border-accent/25", glow: "rgba(210,154,78,0.10)", spark: CHART.accent },
  info: { icon: "text-info", ring: "border-info/25", glow: "rgba(95,146,194,0.10)", spark: CHART.info },
  success: { icon: "text-success", ring: "border-success/25", glow: "rgba(62,192,138,0.10)", spark: CHART.success },
  danger: { icon: "text-danger", ring: "border-danger/25", glow: "rgba(229,72,77,0.10)", spark: CHART.danger },
  neutral: { icon: "text-muted", ring: "border-border", glow: "rgba(152,162,176,0.07)", spark: CHART.text }
} as const;

/**
 * Flagship KPI card — matches the reference dashboard: icon chip, label, large
 * tabular value, delta pill vs. previous period, and an embedded sparkline.
 */
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
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className={`group relative overflow-hidden rounded-2xl border ${t.ring} bg-surface p-4 elevate transition-colors hover:border-border-strong`}
    >
      <div
        className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full opacity-60 blur-2xl transition group-hover:opacity-100"
        style={{ background: t.glow }}
      />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon && (
            <span className={`grid h-8 w-8 place-items-center rounded-lg border border-border bg-bg-2 ${t.icon}`}>
              {icon}
            </span>
          )}
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-faint">{label}</span>
        </div>
        {typeof delta === "number" && (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-semibold ${
              up ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
            }`}
          >
            {up ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>

      <div className="mt-3 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <AnimatedValue
            value={value}
            className="block truncate text-[26px] font-semibold leading-none tabular text-text"
          />
          {typeof delta === "number" && <div className="mt-1.5 text-[11px] text-faint">{deltaLabel}</div>}
        </div>
        {spark && spark.length > 1 && (
          <div className="h-10 w-24 shrink-0">
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
