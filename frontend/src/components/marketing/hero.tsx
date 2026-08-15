"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Play } from "lucide-react";

import { InvestigationGraph } from "./investigation-graph";
import { Particles } from "./particles";

const TRUSTED = ["Government", "Auditors", "Compliance Teams", "Investigators"];

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay: 0.1 + i * 0.08, ease: [0.22, 1, 0.36, 1] as const }
  })
};

export function Hero() {
  return (
    <section className="relative flex min-h-screen items-center overflow-hidden pt-24">
      {/* backdrop layers */}
      <div aria-hidden className="mkt-grid absolute inset-0" />
      <div aria-hidden className="mkt-emerald-wash absolute inset-0" />
      <Particles count={20} />

      <div className="relative mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-12 px-6 lg:grid-cols-2">
        {/* left — copy */}
        <div>
          <motion.div
            custom={0}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-bg-2/60 px-3 py-1 text-xs font-medium text-muted"
          >
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
            </span>
            Procurement intelligence platform
          </motion.div>

          <h1 className="text-6xl font-semibold leading-[0.98] tracking-tight text-text sm:text-7xl">
            <motion.span custom={1} variants={fadeUp} initial="hidden" animate="show" className="block">
              Evidence.
            </motion.span>
            <motion.span
              custom={2}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="block bg-gradient-to-r from-accent to-accent-hi bg-clip-text text-transparent"
            >
              Connected.
            </motion.span>
          </h1>

          <motion.p
            custom={3}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="mt-6 max-w-md text-lg leading-relaxed text-muted"
          >
            Turn fragmented procurement records into one intelligent investigation workspace.
          </motion.p>

          <motion.div
            custom={4}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <Link
              href="/investigate"
              className="group inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-bg transition-all hover:bg-accent-hi"
            >
              Start Investigation
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <button
              type="button"
              className="group inline-flex items-center gap-2 rounded-xl border border-border-strong bg-bg-2/50 px-5 py-3 text-sm font-semibold text-text transition-all hover:border-accent/40"
            >
              <Play className="h-3.5 w-3.5 fill-current text-accent" />
              Watch Demo
            </button>
          </motion.div>

          <motion.div custom={5} variants={fadeUp} initial="hidden" animate="show" className="mt-12">
            <div className="t-label text-faint">
              Trusted by
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
              {TRUSTED.map((t) => (
                <span key={t} className="text-sm font-medium text-muted">
                  {t}
                </span>
              ))}
            </div>
          </motion.div>
        </div>

        {/* right — floating investigation graph */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="relative"
        >
          <div className="mkt-glass mkt-glass-hi relative rounded-3xl p-4">
            <InvestigationGraph className="aspect-[520/460] w-full" />
          </div>
        </motion.div>
      </div>

      {/* scroll cue */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4 }}
        className="absolute bottom-6 left-1/2 -translate-x-1/2 text-[11px] font-medium uppercase tracking-[0.16em] text-faint"
      >
        Scroll to explore
      </motion.div>
    </section>
  );
}
