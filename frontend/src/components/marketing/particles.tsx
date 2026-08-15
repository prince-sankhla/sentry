"use client";

import { useMemo } from "react";

/**
 * Tiny drifting emerald particles. Deterministic pseudo-random placement (seeded)
 * so server and client render identically — no hydration mismatch.
 */
export function Particles({ count = 18, className = "" }: { count?: number; className?: string }) {
  const dots = useMemo(() => {
    // simple LCG for stable positions across SSR/CSR
    let seed = 1337;
    const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
    return Array.from({ length: count }, () => ({
      left: `${(rand() * 100).toFixed(2)}%`,
      top: `${(rand() * 100).toFixed(2)}%`,
      size: `${(rand() * 2 + 1).toFixed(1)}px`,
      dur: `${(rand() * 6 + 7).toFixed(1)}s`,
      delay: `${(rand() * 6).toFixed(1)}s`,
      opacity: (rand() * 0.4 + 0.2).toFixed(2)
    }));
  }, [count]);

  return (
    <div aria-hidden className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      {dots.map((d, i) => (
        <span
          key={i}
          className="mkt-particle"
          style={
            {
              left: d.left,
              top: d.top,
              width: d.size,
              height: d.size,
              opacity: Number(d.opacity),
              "--dur": d.dur,
              "--delay": d.delay
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}
