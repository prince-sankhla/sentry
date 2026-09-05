"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Building2,
  FileCheck2,
  FileSearch,
  GitBranch,
  Landmark,
  Newspaper,
  Scale,
  SearchCheck,
  ShieldCheck,
  Siren,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const OBJECTS: { icon: LucideIcon; label: string; detail: string; href: string }[] = [
  { icon: Building2, label: "Companies", detail: "Entity history, relationships and procurement footprint", href: "/companies" },
  { icon: FileSearch, label: "Tenders", detail: "Tender records, awards, documents and review signals", href: "/tenders" },
  { icon: Landmark, label: "Buyers", detail: "Procuring-entity activity, suppliers and patterns", href: "/buyers" },
  { icon: FileCheck2, label: "Awards", detail: "Award history connected back to the underlying tender", href: "/awards" },
  { icon: GitBranch, label: "Relationships", detail: "Buyer ↔ tender ↔ supplier ↔ award connections", href: "/graph" },
  { icon: Activity, label: "Live monitoring", detail: "Watch procurement activity and surface review leads", href: "/monitoring" },
];

const MODES: { icon: LucideIcon; title: string; detail: string }[] = [
  { icon: Users, title: "Public Investigator", detail: "Start with an entity or tender and build a source-backed investigation." },
  { icon: Newspaper, title: "Journalist / Researcher", detail: "Trace patterns across time, relationships, evidence gaps and context." },
  { icon: ShieldCheck, title: "Government / Audit", detail: "Prioritise review signals, investigate cases and prepare human-led action." },
];

const PHASES = [
  ["01", "Intelligence", "Assemble known records, relationships and signals."],
  ["02", "Evidence gaps", "Show what is missing before conclusions are drawn."],
  ["03", "Corroboration", "Test retrieved or submitted evidence against known facts."],
  ["04", "Assessment", "Produce the evidence-backed position and next action."],
];

export function SectionCapabilities() {
  return (
    <section className="relative overflow-hidden border-y border-border bg-bg-2/25">
      <div aria-hidden className="mkt-grid absolute inset-0 opacity-40" />
      <div className="relative mx-auto max-w-6xl px-6 py-32">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.65 }}
          className="mx-auto max-w-2xl text-center"
        >
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">The investigation surface</div>
          <h2 className="text-4xl font-semibold leading-tight tracking-tight text-text sm:text-5xl">
            One entry point.
            <br />
            <span className="text-muted">Every investigation layer.</span>
          </h2>
          <p className="mt-5 text-lg leading-relaxed text-muted">
            SENTRY is not just a tender viewer. The same investigation model follows the entity across records, relationships, web context, evidence, monitoring and human review.
          </p>
        </motion.div>

        <div className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {OBJECTS.map(({ icon: Icon, label, detail, href }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.45, delay: i * 0.06 }}
            >
              <Link href={href} className="group block h-full rounded-2xl border border-border bg-surface/70 p-5 transition-all duration-200 hover:-translate-y-1 hover:border-accent/30 hover:bg-surface">
                <div className="flex items-start gap-4">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-accent/25 bg-accent/[0.07] text-accent transition-transform group-hover:scale-105">
                    <Icon className="h-4.5 w-4.5" />
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                      {label}
                      <ArrowRight className="h-3.5 w-3.5 text-faint transition-transform group-hover:translate-x-1 group-hover:text-accent" />
                    </div>
                    <p className="mt-1.5 text-[12px] leading-relaxed text-faint">{detail}</p>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>

        <div className="mt-20 grid gap-8 lg:grid-cols-[1fr_1.2fr] lg:items-center">
          <div>
            <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">Three operating modes</div>
            <h3 className="text-3xl font-semibold tracking-tight text-text sm:text-4xl">Same evidence.<br /><span className="text-muted">Different mission.</span></h3>
            <p className="mt-4 max-w-md text-sm leading-6 text-muted">
              Roles change the workspace emphasis, not the underlying evidence or deterministic risk calculations.
            </p>
            <Link href="/investigate" className="group mt-6 inline-flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-hi">
              Enter investigation workspace <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
          <div className="grid gap-3">
            {MODES.map(({ icon: Icon, title, detail }, i) => (
              <motion.div key={title} initial={{ opacity: 0, x: 18 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.45, delay: i * 0.08 }} className="mkt-glass flex items-start gap-4 rounded-2xl p-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent"><Icon className="h-4 w-4" /></span>
                <div><div className="text-sm font-semibold text-text">{title}</div><p className="mt-1 text-[12px] leading-relaxed text-faint">{detail}</p></div>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="mt-20 rounded-3xl border border-accent/20 bg-accent/[0.035] p-6 sm:p-8">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent"><SearchCheck className="h-3.5 w-3.5" /> Investigation protocol</div>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            {PHASES.map(([number, title, detail], i) => (
              <motion.div key={number} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.07 }} className="rounded-2xl border border-border bg-surface/60 p-4">
                <div className="font-mono text-[10px] tracking-[0.18em] text-accent">{number}</div>
                <div className="mt-2 text-sm font-semibold text-text">{title}</div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-faint">{detail}</p>
              </motion.div>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-border pt-4 text-[10.5px] text-faint">
            <span className="inline-flex items-center gap-1.5"><Scale className="h-3.5 w-3.5 text-accent" /> Web research adds context, not proof.</span>
            <span className="inline-flex items-center gap-1.5"><Siren className="h-3.5 w-3.5 text-accent" /> Signals prioritise human review.</span>
            <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-accent" /> Evidence stays traceable.</span>
          </div>
        </div>
      </div>
    </section>
  );
}
