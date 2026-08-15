"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Cpu, Database, GitBranch, Lock, Search, Shield } from "lucide-react";

const LAYERS = [
  {
    n: "01",
    title: "Official source connectors",
    body: "Direct integrations with GeM, CPPP, Odisha e-Proc, and World Bank procurement portals. Records are pulled from official APIs and government feeds — never scraped.",
    icon: Database,
    accent: "border-accent/30 bg-accent/[0.06] text-accent"
  },
  {
    n: "02",
    title: "Deterministic screening engine",
    body: "12 rules applied identically to every record. No machine-learning inference, no probability estimates. Every finding states the exact records that triggered it.",
    icon: Search,
    accent: "border-info/30 bg-info/[0.06] text-info"
  },
  {
    n: "03",
    title: "Entity resolution layer",
    body: "Canonical identity matching across name variants, registration numbers, and aliases. The same supplier never hides behind two different spellings.",
    icon: GitBranch,
    accent: "border-accent/30 bg-accent/[0.06] text-accent"
  },
  {
    n: "04",
    title: "Evidence preservation",
    body: "Every piece of evidence is archived at retrieval time with a SHA-256 integrity hash. Investigations survive long after the original government page goes offline.",
    icon: Lock,
    accent: "border-success/30 bg-success/[0.06] text-success"
  },
  {
    n: "05",
    title: "Grounding guard",
    body: "AI summaries are checked against the cited evidence before display. Any claim the AI cannot ground to a specific official record is suppressed.",
    icon: Shield,
    accent: "border-info/30 bg-info/[0.06] text-info"
  },
  {
    n: "06",
    title: "Explainable output",
    body: "Every finding links to its triggering records. Every AI paragraph shows its evidence count, source list, and grounding status. Nothing is hidden.",
    icon: BadgeCheck,
    accent: "border-success/30 bg-success/[0.06] text-success"
  }
];

const TRUST_STATS = [
  { value: "100%", label: "Deterministic findings" },
  { value: "SHA-256", label: "Evidence integrity" },
  { value: "0", label: "Invented facts" },
  { value: "Audit-ready", label: "Investigation export" }
];

export function SectionArchitecture() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="mb-16 max-w-xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="t-label mb-4 text-accent">Architecture</div>
          <h2 className="text-4xl font-semibold leading-tight tracking-tight text-text sm:text-5xl">
            Built for accountability.
            <br />
            <span className="text-muted">Not for demos.</span>
          </h2>
          <p className="mt-6 text-lg leading-relaxed text-muted">
            Six layers of verification — from source connector to final report. Every
            decision is traceable. Every output is reproducible. Every claim is grounded
            in official evidence you can independently verify.
          </p>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {LAYERS.map((l, i) => {
          const Icon = l.icon;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.45, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] }}
              className="group rounded-2xl border border-border bg-surface/40 p-5 transition-colors duration-200 hover:border-border-strong hover:bg-surface/70"
            >
              <div className="mb-4 flex items-center gap-3">
                <span className={`grid h-9 w-9 place-items-center rounded-lg border ${l.accent}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="font-mono text-[10px] text-faint">{l.n}</span>
              </div>
              <div className="text-[13.5px] font-semibold leading-snug text-text">{l.title}</div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-faint">{l.body}</p>
            </motion.div>
          );
        })}
      </div>

      {/* trust stats bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="mt-14 grid grid-cols-2 gap-4 sm:grid-cols-4"
      >
        {TRUST_STATS.map((s) => (
          <div key={s.label} className="rounded-xl border border-border bg-bg-2/40 py-5 text-center">
            <div className="text-2xl font-semibold tracking-tight text-accent">{s.value}</div>
            <div className="mt-1.5 text-[11.5px] text-faint">{s.label}</div>
          </div>
        ))}
      </motion.div>

      {/* bottom note */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="mt-10 flex items-center justify-center gap-2 text-[12px] text-faint"
      >
        <Cpu className="h-3.5 w-3.5 text-accent" />
        <span>
          Fully open-source. Runs on-premise. No data leaves the investigator's environment.
        </span>
      </motion.div>
    </section>
  );
}
