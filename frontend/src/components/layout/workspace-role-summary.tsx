"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Eye, FileSearch, ShieldCheck } from "lucide-react";
import { getStoredWorkspaceRole, WORKSPACE_ROLES, type WorkspaceRole } from "./workspace-role";

const FOCUS: Record<WorkspaceRole, string[]> = {
  public_investigator: ["Verified entity lookup", "Evidence and provenance", "Review signals"],
  journalist_researcher: ["Longitudinal patterns", "Relationship analysis", "Evidence gaps and corroboration"],
  government_audit: ["Priority review signals", "Cross-record verification", "Human-led assessment"]
};

export function WorkspaceRoleSummary() {
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

  const definition = WORKSPACE_ROLES.find((item) => item.id === role) ?? WORKSPACE_ROLES[0];
  const Icon = definition.icon;

  return (
    <section className="rounded-2xl border border-border bg-surface/60 p-5">
      <div className="flex items-start gap-3.5">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-accent/25 bg-accent/[0.08] text-accent">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Active workspace role</div>
          <div className="mt-1 text-base font-semibold text-text">{definition.label}</div>
          <p className="mt-1 text-xs leading-relaxed text-muted">{definition.description}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {FOCUS[role].map((item) => (
          <div key={item} className="flex items-center gap-2 rounded-lg border border-border bg-bg-2/40 px-2.5 py-2 text-[11px] text-muted">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
            <span>{item}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 text-[10.5px] leading-relaxed text-faint">
        Role changes affect workspace emphasis and navigation only. The underlying procurement records, evidence provenance, and deterministic screening remain unchanged.
      </div>
    </section>
  );
}
