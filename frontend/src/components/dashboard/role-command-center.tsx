"use client";

import Link from "next/link";
import { ArrowRight, Eye, FileSearch, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { getStoredWorkspaceRole, WORKSPACE_ROLES, type WorkspaceRole } from "@/components/layout/workspace-role";

const CONFIG: Record<WorkspaceRole, {
  eyebrow: string;
  title: string;
  description: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref: string;
  secondaryLabel: string;
  steps: [string, string, string];
}> = {
  public_investigator: {
    eyebrow: "Public investigation",
    title: "Start with a verified entity",
    description: "Review grounded procurement records, understand the available evidence, and identify what still needs verification.",
    primaryHref: "/investigations",
    primaryLabel: "Start an investigation",
    secondaryHref: "/tenders",
    secondaryLabel: "Browse tender records",
    steps: ["Resolve the entity", "Review evidence", "Identify next checks"]
  },
  journalist_researcher: {
    eyebrow: "Research workspace",
    title: "Trace the pattern behind the record",
    description: "Move across time, relationships and evidence gaps to build a corroborated research trail without treating signals as conclusions.",
    primaryHref: "/investigations",
    primaryLabel: "Open research workspace",
    secondaryHref: "/graph",
    secondaryLabel: "Explore relationships",
    steps: ["Compare across time", "Connect entities", "Corroborate sources"]
  },
  government_audit: {
    eyebrow: "Audit workspace",
    title: "Prioritise review, then verify",
    description: "Start from review signals, inspect connected procurement records, and preserve the human decision boundary throughout assessment.",
    primaryHref: "/risk",
    primaryLabel: "Open review queue",
    secondaryHref: "/investigations",
    secondaryLabel: "Open investigation workspace",
    steps: ["Prioritise signals", "Verify records", "Prepare human review"]
  }
};

const ICONS = {
  public_investigator: Eye,
  journalist_researcher: FileSearch,
  government_audit: ShieldCheck
};

export function RoleCommandCenter() {
  const [role, setRole] = useState<WorkspaceRole>("public_investigator");

  useEffect(() => {
    setRole(getStoredWorkspaceRole());
    const onChange = (event: Event) => {
      const next = (event as CustomEvent<WorkspaceRole>).detail;
      if (WORKSPACE_ROLES.some((item) => item.id === next)) setRole(next);
    };
    window.addEventListener("sentry:workspace-role", onChange);
    return () => window.removeEventListener("sentry:workspace-role", onChange);
  }, []);

  const config = CONFIG[role];
  const Icon = ICONS[role];

  return (
    <section className="rounded-2xl border border-border bg-surface elevate">
      <div className="relative overflow-hidden px-5 py-5 sm:px-6 sm:py-6">
        <div className="pointer-events-none absolute -right-16 -top-20 h-48 w-48 rounded-full bg-accent/[0.06] blur-3xl" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent">
              <Icon className="h-3.5 w-3.5" />
              {config.eyebrow}
            </div>
            <h2 className="mt-2 text-[21px] font-semibold tracking-tight text-text">{config.title}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{config.description}</p>
          </div>
          <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col">
            <Link href={config.primaryHref} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-bg transition hover:brightness-110">
              {config.primaryLabel}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href={config.secondaryHref} className="inline-flex h-10 items-center justify-center rounded-xl border border-border bg-bg-2/60 px-4 text-sm font-medium text-muted transition hover:border-border-strong hover:text-text">
              {config.secondaryLabel}
            </Link>
          </div>
        </div>
      </div>
      <div className="grid border-t border-border bg-bg-2/30 md:grid-cols-3">
        {config.steps.map((step, index) => (
          <div key={step} className="flex items-center gap-2.5 border-b border-border px-5 py-3 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-accent/25 bg-accent/[0.07] font-mono text-[9px] font-semibold text-accent">{String(index + 1).padStart(2, "0")}</span>
            <span className="text-[11.5px] font-medium text-muted">{step}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
