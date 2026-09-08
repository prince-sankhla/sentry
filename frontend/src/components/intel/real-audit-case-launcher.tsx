"use client";

import { ArrowRight, FileSearch, ShieldAlert } from "lucide-react";

const CASES = [
  {
    key: "delhi-cwg",
    title: "Delhi Street-Light Modernisation — CWG-2010",
    subtitle: "CAG performance audit reconstruction",
    signal: "₹31.07 crore avoidable extra expenditure reported on imported luminaries",
  },
  {
    key: "dhanbad-led",
    title: "Dhanbad Municipal LED Street Lights",
    subtitle: "CAG compliance audit reconstruction",
    signal: "171 of 237 jointly verified lights reported non-functional/improper (72%)",
  },
] as const;

export function RealAuditCaseLauncher() {
  return (
    <section className="mt-8 rounded-3xl border border-accent/20 bg-accent/[0.035] p-5 md:p-7">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-accent"><ShieldAlert className="h-3.5 w-3.5" /> Judge demo cases · official audit record</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-text">Start with a real audited investigation</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">These are source-backed CAG case reconstructions. SENTRY walks from procurement evidence to risk assessment, alternative explanations and a physical-verification gate.</p>
        </div>
        <div className="text-[11px] text-faint">Audit evidence ≠ automatic fraud finding</div>
      </div>
      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {CASES.map((item) => (
          <a key={item.key} href={`/investigate?case=${item.key}`} className="group rounded-2xl border border-border bg-surface p-5 transition hover:border-accent/40">
            <div className="flex items-start justify-between gap-4"><div><div className="text-[10px] font-semibold uppercase tracking-[.14em] text-faint">{item.subtitle}</div><div className="mt-2 text-base font-semibold text-text">{item.title}</div><p className="mt-2 text-xs leading-5 text-muted">{item.signal}</p></div><FileSearch className="mt-0.5 h-4 w-4 shrink-0 text-accent" /></div>
            <div className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-accent">Open investigation <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" /></div>
          </a>
        ))}
      </div>
    </section>
  );
}
