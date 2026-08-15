"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { EASE } from "@/lib/motion";

/**
 * Floating panel — the workspace's structural surface.
 *
 * Three weights, all sharing the same hairline + radius so they stack without
 * visual argument:
 *   `flat`    matte aluminium, sits in the page flow
 *   `float`   lifted, for panels that overlay content
 *   `glass`   very light glassmorphism, for chrome over a live canvas
 */

export type PanelTone = "flat" | "float" | "glass";

const TONES: Record<PanelTone, string> = {
  flat: "border border-border bg-surface elevate",
  float: "border border-border bg-surface float",
  glass: "glass glass-hi"
};

export function Panel({
  children,
  tone = "flat",
  className = "",
  padded = false
}: {
  children: ReactNode;
  tone?: PanelTone;
  className?: string;
  /** Applies the editorial padding tier. Omit when the panel supplies its own. */
  padded?: boolean;
}) {
  return (
    <section
      className={`overflow-hidden rounded-2xl ${TONES[tone]} ${
        padded ? "p-6 md:p-8" : ""
      } ${className}`}
    >
      {children}
    </section>
  );
}

/**
 * Panel header — eyebrow, title, optional action rail.
 * Sits flush against the panel's top edge with its own hairline.
 */
export function PanelHeader({
  title,
  eyebrow,
  subtitle,
  action,
  icon,
  className = ""
}: {
  title: ReactNode;
  eyebrow?: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex items-start justify-between gap-4 border-b border-border bg-bg-2/40 px-6 py-4 ${className}`}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-surface text-accent">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          {eyebrow && <div className="t-label mb-1">{eyebrow}</div>}
          <h2 className="truncate text-[15px] font-semibold tracking-[-0.014em] text-text">
            {title}
          </h2>
          {subtitle && (
            <div className="mt-1 text-[13px] leading-relaxed text-muted">
              {subtitle}
            </div>
          )}
        </div>
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  );
}

/** Body wrapper applying the chosen density tier. */
export function PanelBody({
  children,
  density = "editorial",
  className = ""
}: {
  children: ReactNode;
  density?: "editorial" | "data";
  className?: string;
}) {
  return (
    <div className={`${density === "editorial" ? "p-6" : "p-4"} ${className}`}>
      {children}
    </div>
  );
}

/**
 * Animated panel — same surface, with the standard entrance and an optional
 * hover lift. Use for panels that appear in response to an action.
 */
export function MotionPanel({
  children,
  tone = "float",
  className = "",
  delay = 0,
  lift = false
}: {
  children: ReactNode;
  tone?: PanelTone;
  className?: string;
  delay?: number;
  lift?: boolean;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10, scale: 0.99 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, delay, ease: EASE }}
      whileHover={lift ? { y: -2 } : undefined}
      className={`overflow-hidden rounded-2xl ${TONES[tone]} ${className}`}
    >
      {children}
    </motion.section>
  );
}
