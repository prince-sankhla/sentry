"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { InvestigationGraph } from "./investigation-graph";
import { NODE_ORDER, NODE_TYPES } from "./node-types";

/**
 * Section 5 — product preview inside a floating laptop frame. The screen reuses
 * the real InvestigationGraph component (same motif as the workspace) plus a
 * live node-type legend — no fabricated cards, scores, or statistics.
 */
export function SectionPreview() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1fr_1.3fr]">
        {/* copy */}
        <div>
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
            Product
          </div>
          <h2 className="text-4xl font-semibold leading-tight tracking-tight text-text sm:text-5xl">
            One workspace.
            <br />
            <span className="text-muted">Every connection.</span>
          </h2>
          <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
            Built for complex investigations, designed for clarity. Every entity, award, and
            document in a single graph you can follow end to end.
          </p>

          <div className="mt-6 flex flex-wrap gap-2">
            {NODE_ORDER.map((kind) => {
              const { label, icon: Icon } = NODE_TYPES[kind];
              return (
                <span
                  key={kind}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/60 px-2.5 py-1.5 text-xs font-medium text-muted"
                >
                  <Icon className="h-3.5 w-3.5 text-accent" />
                  {label}
                </span>
              );
            })}
          </div>

          <Link
            href="/investigate"
            className="group mt-8 inline-flex items-center gap-2 rounded-xl border border-border-strong bg-bg-2/50 px-5 py-3 text-sm font-semibold text-text transition-all hover:border-accent/40"
          >
            Explore Product
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>

        {/* laptop */}
        <motion.div
          initial={{ opacity: 0, y: 40, rotateX: 8 }}
          whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          style={{ perspective: 1200 }}
        >
          {/* lid / screen */}
          <div className="mkt-glass mkt-glass-hi relative overflow-hidden rounded-t-2xl border-b-0 p-2.5">
            {/* menu bar */}
            <div className="mb-2 flex items-center gap-1.5 px-1">
              <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              <span className="h-2.5 w-2.5 rounded-full bg-border-strong" />
              <span className="ml-3 text-[10px] font-medium text-faint">
                sentry · investigation workspace
              </span>
            </div>
            <div className="relative rounded-lg border border-border bg-bg">
              <InvestigationGraph className="aspect-[16/10] w-full" />
            </div>
          </div>
          {/* base */}
          <div className="relative">
            <div className="h-3 rounded-b-2xl bg-gradient-to-b from-border to-bg-2" />
            <div className="mx-auto h-1 w-24 rounded-b-lg bg-border-strong" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
