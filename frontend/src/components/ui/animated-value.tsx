"use client";

import { animate, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";

/**
 * Counts a formatted metric up to its final value the first time it scrolls
 * into view. Works on already-formatted strings ("₹1.24Cr", "1,204", "38%"):
 * it isolates the first numeric run, animates that, and re-applies the original
 * prefix, suffix, decimal precision, and thousands grouping. Non-numeric values
 * render verbatim. Respects prefers-reduced-motion by snapping to the value.
 */
export function AnimatedValue({
  value,
  className,
  duration = 0.9
}: {
  value: string;
  className?: string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [display, setDisplay] = useState<string>(() => zeroed(value));

  useEffect(() => {
    const parsed = parse(value);
    if (!parsed) {
      setDisplay(value);
      return;
    }
    if (!inView) return;

    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setDisplay(value);
      return;
    }

    const controls = animate(0, parsed.target, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(format(v, parsed)),
      onComplete: () => setDisplay(value)
    });
    return () => controls.stop();
  }, [value, inView, duration]);

  return (
    <span ref={ref} className={className}>
      {display}
    </span>
  );
}

type Parsed = {
  prefix: string;
  suffix: string;
  target: number;
  decimals: number;
  grouped: boolean;
};

function parse(raw: string): Parsed | null {
  const match = raw.match(/^(.*?)(-?[\d,]+(?:\.\d+)?)(.*)$/);
  if (!match) return null;
  const [, prefix, num, suffix] = match;
  const decimals = num.includes(".") ? num.split(".")[1].length : 0;
  const target = Number(num.replace(/,/g, ""));
  if (Number.isNaN(target)) return null;
  return { prefix, suffix, target, decimals, grouped: num.includes(",") };
}

function format(v: number, p: Parsed): string {
  const body = p.grouped
    ? v.toLocaleString("en-IN", {
        minimumFractionDigits: p.decimals,
        maximumFractionDigits: p.decimals
      })
    : v.toFixed(p.decimals);
  return `${p.prefix}${body}${p.suffix}`;
}

function zeroed(raw: string): string {
  const p = parse(raw);
  return p ? format(0, p) : raw;
}
