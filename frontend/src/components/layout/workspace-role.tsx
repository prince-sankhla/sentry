"use client";

import { Check, ChevronDown, Eye, FileSearch, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type WorkspaceRole = "public_investigator" | "journalist_researcher" | "government_audit";

export type WorkspaceRoleDefinition = {
  id: WorkspaceRole;
  label: string;
  shortLabel: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
};

export const WORKSPACE_ROLES: WorkspaceRoleDefinition[] = [
  {
    id: "public_investigator",
    label: "Public Investigator",
    shortLabel: "Public",
    description: "Investigate a procurement entity, understand the evidence, and preserve source provenance.",
    icon: Eye
  },
  {
    id: "journalist_researcher",
    label: "Journalist / Researcher",
    shortLabel: "Research",
    description: "Trace patterns across time, relationships, evidence gaps, and supporting sources.",
    icon: FileSearch
  },
  {
    id: "government_audit",
    label: "Government / Audit",
    shortLabel: "Audit",
    description: "Prioritise review signals, inspect connected procurement records, and prepare human-led review.",
    icon: ShieldCheck
  }
];

const KEY = "sentry.workspace-role";
const DEFAULT_ROLE: WorkspaceRole = "public_investigator";

function isWorkspaceRole(value: unknown): value is WorkspaceRole {
  return WORKSPACE_ROLES.some((role) => role.id === value);
}

export function getStoredWorkspaceRole(): WorkspaceRole {
  if (typeof window === "undefined") return DEFAULT_ROLE;
  try {
    const raw = window.localStorage.getItem(KEY);
    return isWorkspaceRole(raw) ? raw : DEFAULT_ROLE;
  } catch {
    return DEFAULT_ROLE;
  }
}

export function persistWorkspaceRole(role: WorkspaceRole): void {
  try {
    window.localStorage.setItem(KEY, role);
    window.dispatchEvent(new CustomEvent("sentry:workspace-role", { detail: role }));
  } catch {
    /* local-only preference; ignore storage failures */
  }
}

export function WorkspaceRoleSwitcher() {
  const [role, setRole] = useState<WorkspaceRole>(DEFAULT_ROLE);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setRole(getStoredWorkspaceRole());

    function onRoleChange(event: Event) {
      const next = (event as CustomEvent<WorkspaceRole>).detail;
      if (isWorkspaceRole(next)) setRole(next);
    }

    function onPointerDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }

    window.addEventListener("sentry:workspace-role", onRoleChange);
    window.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("sentry:workspace-role", onRoleChange);
      window.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  const current = WORKSPACE_ROLES.find((item) => item.id === role) ?? WORKSPACE_ROLES[0];
  const CurrentIcon = current.icon;

  function select(next: WorkspaceRole) {
    setRole(next);
    persistWorkspaceRole(next);
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative hidden lg:block">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-10 items-center gap-2 rounded-xl border border-border bg-surface/60 px-2.5 text-left transition-colors duration-200 hover:border-border-strong hover:bg-surface"
      >
        <span className="grid h-6 w-6 place-items-center rounded-lg border border-accent/25 bg-accent/[0.08] text-accent">
          <CurrentIcon className="h-3.5 w-3.5" />
        </span>
        <span className="hidden xl:block">
          <span className="block text-[9px] font-semibold uppercase tracking-[0.12em] text-faint">Workspace</span>
          <span className="block text-[11.5px] font-medium leading-tight text-text">{current.shortLabel}</span>
        </span>
        <ChevronDown className={`h-3.5 w-3.5 text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-[calc(100%+8px)] z-50 w-80 overflow-hidden rounded-2xl border border-border bg-bg-2 p-2 shadow-2xl">
          <div className="px-2.5 pb-2 pt-1">
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">Investigation role</div>
            <div className="mt-1 text-[11.5px] leading-relaxed text-muted">
              Choose the workspace emphasis. This changes presentation only; it does not change underlying evidence or risk calculations.
            </div>
          </div>
          <div className="space-y-1">
            {WORKSPACE_ROLES.map((item) => {
              const Icon = item.icon;
              const active = item.id === role;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => select(item.id)}
                  className={`flex w-full items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${
                    active
                      ? "border-accent/25 bg-accent/[0.07]"
                      : "border-transparent hover:border-border hover:bg-surface"
                  }`}
                >
                  <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border ${active ? "border-accent/25 bg-accent/10 text-accent" : "border-border bg-bg text-muted"}`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2 text-[12.5px] font-semibold text-text">
                      {item.label}
                      {active && <span className="text-[9px] font-semibold uppercase tracking-wide text-accent">Active</span>}
                    </span>
                    <span className="mt-0.5 block text-[11px] leading-relaxed text-faint">{item.description}</span>
                  </span>
                  {active && <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
