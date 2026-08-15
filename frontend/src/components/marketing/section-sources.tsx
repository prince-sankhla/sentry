"use client";

import { motion } from "framer-motion";
import { Building2, FileText, Gavel, Landmark, ScrollText } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Section 6 — trusted sources. Glass cards that gently lift on hover. Describes
 * the categories of official data SENTRY connects (no provider logos invented).
 */

const SOURCES: { icon: LucideIcon; label: string; detail: string }[] = [
  { icon: Landmark, label: "Government Portals", detail: "National & state procurement systems" },
  { icon: Building2, label: "Company Registry", detail: "Entity & ownership records" },
  { icon: Gavel, label: "Court Records", detail: "Public legal filings" },
  { icon: ScrollText, label: "Tender Records", detail: "Notices, awards, corrigenda" },
  { icon: FileText, label: "Official Documents", detail: "Primary source attachments" }
];

export function SectionSources() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="mx-auto mb-14 max-w-2xl text-center">
        <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          Trusted sources
        </div>
        <h2 className="text-4xl font-semibold tracking-tight text-text sm:text-5xl">
          We connect verified data from official sources
        </h2>
        <p className="mt-4 text-muted">
          Every record traces back to its origin. Provenance is preserved end to end.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        {SOURCES.map((source, i) => {
          const Icon = source.icon;
          return (
            <motion.div
              key={source.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.55, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ y: -6 }}
              className="mkt-glass group flex flex-col items-center rounded-2xl p-6 text-center transition-colors hover:border-accent/30"
            >
              <span className="grid h-12 w-12 place-items-center rounded-xl border border-accent/25 bg-accent/[0.08] text-accent transition-transform group-hover:scale-105">
                <Icon className="h-5 w-5" />
              </span>
              <div className="mt-4 text-sm font-semibold text-text">{source.label}</div>
              <div className="mt-1.5 text-xs leading-snug text-muted">{source.detail}</div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
