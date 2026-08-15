"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Logo } from "./logo";
import { Particles } from "./particles";

function GithubMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12 .5C5.7.5.5 5.7.5 12c0 5.1 3.3 9.4 7.9 10.9.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.6 18.3 5 18.3 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6 4.6-1.5 7.9-5.8 7.9-10.9C23.5 5.7 18.3.5 12 .5Z" />
    </svg>
  );
}

/**
 * Final section — huge typography statement + minimal CTAs, and a quiet footer.
 */
export function SectionCta() {
  return (
    <section className="relative overflow-hidden px-6 pb-16 pt-32">
      <div aria-hidden className="mkt-emerald-wash absolute inset-0" />
      <Particles count={14} />

      <div className="relative mx-auto max-w-4xl text-center">
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="text-5xl font-semibold leading-[1.02] tracking-tight text-text sm:text-7xl"
        >
          Evidence over
          <br />
          <span className="bg-gradient-to-r from-accent to-accent-hi bg-clip-text text-transparent">
            assumptions.
          </span>
        </motion.h2>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-3"
        >
          <Link
            href="/investigate"
            className="group inline-flex items-center gap-2 rounded-xl bg-accent px-6 py-3.5 text-sm font-semibold text-bg transition-all hover:bg-accent-hi"
          >
            Start Investigation
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <button
            type="button"
            className="rounded-xl border border-border-strong bg-bg-2/50 px-6 py-3.5 text-sm font-semibold text-text transition-all hover:border-accent/40"
          >
            Book Demo
          </button>
          <a
            href="https://github.com/prince-sankhla/sentry"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-xl border border-border-strong bg-bg-2/50 px-6 py-3.5 text-sm font-semibold text-text transition-all hover:border-accent/40"
          >
            <GithubMark className="h-4 w-4" />
            GitHub
          </a>
        </motion.div>
      </div>

      {/* footer */}
      <footer className="relative mx-auto mt-28 max-w-6xl border-t border-border pt-8">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <Logo className="h-7 w-7" />
            <span className="text-sm font-semibold tracking-tight text-text">SENTRY</span>
          </div>
          <p className="text-xs text-faint">
            An oversight tool — surfaces leads for human review, never a determination of wrongdoing.
          </p>
        </div>
      </footer>
    </section>
  );
}
