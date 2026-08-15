"use client";

import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionStyle,
  type MotionValue
} from "framer-motion";
import { useMemo, useRef } from "react";

/**
 * Section 2 — "Why SENTRY". As the section scrolls through the viewport,
 * scattered record fragments (left) converge toward a connected constellation
 * (right): documents fly together, entities merge, connections appear.
 * Scroll-linked via Framer Motion useScroll (no extra libraries).
 */

type Fragment = { sx: number; sy: number; tx: number; ty: number };

// Each fragment owns exactly one useTransform pair — hooks stay unconditional.
function FragmentRect({
  frag,
  converge,
  reduce,
  fill
}: {
  frag: Fragment;
  converge: MotionValue<number>;
  reduce: boolean;
  fill: string;
}) {
  const x = useTransform(converge, [0, 1], [frag.sx - 4.5, frag.tx - 4.5]);
  const y = useTransform(converge, [0, 1], [frag.sy - 5.5, frag.ty - 5.5]);
  return (
    <motion.rect
      width={9}
      height={11}
      rx={1.5}
      fill={fill}
      stroke="#333b48"
      strokeWidth={0.8}
      style={reduce ? { x: frag.tx - 4.5, y: frag.ty - 5.5 } : { x, y }}
    />
  );
}

function EdgeLine({
  frag,
  converge,
  reduce
}: {
  frag: Fragment;
  converge: MotionValue<number>;
  reduce: boolean;
}) {
  const opacity = useTransform(converge, [0.5, 1], [0, 0.4]);
  return (
    <motion.g style={{ opacity: reduce ? 0.4 : opacity } as MotionStyle}>
      <line x1={0} y1={0} x2={frag.tx} y2={frag.ty} stroke="#10b981" strokeWidth={0.8} />
    </motion.g>
  );
}

export function SectionWhy() {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion() ?? false;
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  });

  // 0 = scattered, 1 = converged.
  const converge = useTransform(scrollYProgress, [0.1, 0.55], [0, 1]);
  const coreOpacity = useTransform(converge, [0.3, 0.8], [0.2, 1]);

  const fragments = useMemo<Fragment[]>(() => {
    let seed = 42;
    const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
    return Array.from({ length: 26 }, (_, i) => {
      const angle = (i / 26) * Math.PI * 2;
      const targetR = 60 + (i % 3) * 26;
      return {
        sx: rand() * 300 - 150,
        sy: rand() * 220 - 110,
        tx: Math.cos(angle) * targetR,
        ty: Math.sin(angle) * targetR * 0.7
      };
    });
  }, []);

  return (
    <section ref={ref} className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
        <div>
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
            Why SENTRY
          </div>
          <h2 className="text-4xl font-semibold leading-tight tracking-tight text-text sm:text-5xl">
            Public procurement data isn&rsquo;t missing.
            <br />
            <span className="text-muted">It&rsquo;s fragmented.</span>
          </h2>
          <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
            Records live in hundreds of portals, PDFs, and registers. SENTRY connects the
            evidence — resolving entities, linking awards to tenders, and building one graph
            you can actually investigate.
          </p>
        </div>

        <div className="relative aspect-square">
          <div aria-hidden className="mkt-grid absolute inset-0 rounded-3xl opacity-60" />
          <svg viewBox="-200 -160 400 320" className="relative h-full w-full">
            {fragments.slice(0, 12).map((f, i) => (
              <EdgeLine key={`l-${i}`} frag={f} converge={converge} reduce={reduce} />
            ))}
            <motion.circle cx={0} cy={0} r={14} fill="#10b981" style={{ opacity: reduce ? 1 : coreOpacity } as MotionStyle} />
            {fragments.map((f, i) => (
              <FragmentRect
                key={i}
                frag={f}
                converge={converge}
                reduce={reduce}
                fill={i % 4 === 0 ? "#1d232e" : "#171a21"}
              />
            ))}
          </svg>
        </div>
      </div>
    </section>
  );
}
