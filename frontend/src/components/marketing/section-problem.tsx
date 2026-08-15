"use client";

import { motion, useScroll, useTransform, type MotionStyle } from "framer-motion";
import { AlertTriangle, Clock, Database, FileX, Globe2, Lock } from "lucide-react";
import { useRef } from "react";

const PROBLEMS = [
  {
    icon: Globe2,
    title: "Scattered across hundreds of portals",
    body: "GeM, CPPP, state e-procurement systems, district portals — every department runs its own silo. No single investigator can monitor them all."
  },
  {
    icon: FileX,
    title: "Records disappear without warning",
    body: "Government pages expire, URLs change, PDFs are deleted. Evidence that exists today may be gone tomorrow — and investigations collapse."
  },
  {
    icon: Clock,
    title: "Manual analysis takes weeks",
    body: "Cross-referencing suppliers across tenders, spotting same-day fragmentation, tracing award patterns — each step requires hours of manual work."
  },
  {
    icon: Lock,
    title: "Entity identities are obfuscated",
    body: "The same company appears under dozens of name variations across different portals. Shell structures, related parties, and aliases hide in plain sight."
  },
  {
    icon: Database,
    title: "No audit trail for the investigation itself",
    body: "When investigators share findings, there's no verifiable chain of evidence. Conclusions can't be reproduced, challenged, or defended in tribunal."
  },
  {
    icon: AlertTriangle,
    title: "Patterns only visible at scale",
    body: "Contract fragmentation, single-bidder clusters, bid-rigging timing — these signals only become visible when you can analyse thousands of records at once."
  }
];

export function SectionProblem() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "center center"] });
  const opacity = useTransform(scrollYProgress, [0, 0.4], [0, 1]);
  const y = useTransform(scrollYProgress, [0, 0.4], [32, 0]);

  return (
    <section ref={ref} className="relative mx-auto max-w-6xl px-6 py-32">
      {/* subtle hairline above section */}
      <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <motion.div style={{ opacity, y } as MotionStyle} className="mb-16 max-w-xl">
        <div className="t-label mb-4 text-accent">The problem</div>
        <h2 className="text-4xl font-semibold leading-tight tracking-tight text-text sm:text-5xl">
          Public procurement data exists.
          <br />
          <span className="text-muted">Accountability doesn't.</span>
        </h2>
        <p className="mt-6 text-lg leading-relaxed text-muted">
          Billions of public contracts are awarded every year. The evidence is technically
          public — but fragmented across incompatible systems, unstable URLs, and formats
          designed for compliance, not investigation.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PROBLEMS.map((p, i) => {
          const Icon = p.icon;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] }}
              className="group rounded-2xl border border-border bg-surface/40 p-5 transition-colors duration-200 hover:border-border-strong hover:bg-surface/70"
            >
              <span className="mb-4 grid h-9 w-9 place-items-center rounded-lg border border-border bg-bg-2 text-muted group-hover:border-danger/30 group-hover:bg-danger/10 group-hover:text-danger">
                <Icon className="h-4 w-4" />
              </span>
              <div className="text-[13.5px] font-semibold leading-snug text-text">{p.title}</div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-faint">{p.body}</p>
            </motion.div>
          );
        })}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="mt-12 rounded-2xl border border-accent/20 bg-accent/[0.04] p-6"
      >
        <div className="flex items-start gap-4">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-accent/30 bg-accent/[0.08] text-accent">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div>
            <div className="text-sm font-semibold text-text">The accountability gap</div>
            <p className="mt-1 text-[13px] leading-relaxed text-muted">
              Even when fraud is present, it takes months to prove. By the time investigators
              can connect the dots, contracts have been paid, evidence has disappeared, and
              officials have moved on. SENTRY closes this window.
            </p>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
