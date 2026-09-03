"use client";

import { motion } from "framer-motion";
import { ArrowRight, Database, FileSearch, Network, Sparkles, Waves } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EASE } from "@/lib/motion";

const capabilityCards = [
  { icon: Database, label: "Procurement history", detail: "Tenders · awards · buyers" },
  { icon: Network, label: "Entity graph", detail: "Relationships · identities" },
  { icon: FileSearch, label: "Evidence trail", detail: "Sources · documents · proof" }
];

export function InvestigationLauncher({ suggestions }: { suggestions: string[] }) {
  const router = useRouter();
  const [value, setValue] = useState("");

  function launch(q: string) {
    const query = q.trim();
    if (query) router.push(`/investigate?q=${encodeURIComponent(query)}`);
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: EASE }}
      className="group relative overflow-hidden rounded-[28px] border border-accent/20 bg-surface p-6 shadow-[0_30px_100px_-55px_rgba(16,185,129,0.65)] md:p-9"
    >
      <div className="pointer-events-none absolute inset-0 opacity-60 [background-image:linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] [background-size:28px_28px]" />
      <motion.div
        className="pointer-events-none absolute -right-28 -top-28 h-72 w-72 rounded-full bg-accent/15 blur-3xl"
        animate={{ scale: [1, 1.12, 1], opacity: [0.4, 0.65, 0.4] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="pointer-events-none absolute -bottom-28 left-1/3 h-48 w-48 rounded-full bg-info/10 blur-3xl"
        animate={{ x: [0, 35, 0], opacity: [0.15, 0.3, 0.15] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
            <Sparkles className="h-3.5 w-3.5" /> New investigation
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-bg-2/70 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
            <Waves className="h-3 w-3 text-accent" /> Evidence-first workflow
          </div>
        </div>

        <h2 className="mt-5 max-w-4xl text-2xl font-semibold tracking-[-0.03em] text-text md:text-3xl">
          Investigate any buyer, supplier, tender, or contract.
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted md:text-[15px]">
          One query. SENTRY retrieves procurement history, resolves identities, traces relationships,
          benchmarks comparable records, and builds an auditable evidence trail.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            launch(value);
          }}
          className="mt-7 flex flex-col gap-2.5 sm:flex-row"
        >
          <Input
            fieldSize="lg"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Company, buyer, tender reference, contract…"
            className="flex-1 bg-bg-2/75"
          />
          <Button variant="primary" size="lg" type="submit" className="px-7" trailing={<ArrowRight className="h-4 w-4" />}>
            Run investigation
          </Button>
        </form>

        <div className="mt-6 grid gap-2 md:grid-cols-3">
          {capabilityCards.map(({ icon: Icon, label, detail }, index) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + index * 0.08, duration: 0.4, ease: EASE }}
              className="rounded-2xl border border-border bg-bg-2/65 p-3.5 backdrop-blur-sm transition-colors duration-200 group-hover:border-border-strong"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-text"><Icon className="h-4 w-4 text-accent" />{label}</div>
              <div className="mt-1 text-[11px] text-faint">{detail}</div>
            </motion.div>
          ))}
        </div>

        {suggestions.length > 0 && (
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-faint">Quick start</span>
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => launch(s)}
                className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-muted transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/40 hover:bg-accent/5 hover:text-accent"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.section>
  );
}
