"use client";

import { useMemo, useState } from "react";
import { Archive, CheckCircle2, ClipboardList, Clock3, FileSearch, Flag, FolderOpen, Search, ShieldAlert } from "lucide-react";
import Link from "next/link";
import type { InvestigationReasoning } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Section } from "@/components/ui/card";

type CaseStatus = "open" | "under_review" | "evidence_requested" | "monitoring" | "escalated" | "closed";

type GovernmentCase = {
  id: string;
  subject: string;
  status: CaseStatus;
  priority: "critical" | "high" | "medium" | "low";
  findings: number;
  evidence: number;
  outstanding: number;
  openedAt: string;
  owner: string;
  source: "public_handoff" | "internal_review";
};

const STORAGE_KEY = "sentry.government-cases";

const STATUS_META: Record<CaseStatus, { label: string; icon: typeof FolderOpen; tone: "accent" | "warning" | "success" | "neutral" | "danger" }> = {
  open: { label: "Open", icon: FolderOpen, tone: "accent" },
  under_review: { label: "Under review", icon: FileSearch, tone: "warning" },
  evidence_requested: { label: "Evidence requested", icon: ClipboardList, tone: "warning" },
  monitoring: { label: "Monitoring", icon: Clock3, tone: "neutral" },
  escalated: { label: "Escalated", icon: ShieldAlert, tone: "danger" },
  closed: { label: "Closed", icon: Archive, tone: "success" }
};

const PRIORITY_LABEL: Record<GovernmentCase["priority"], string> = {
  critical: "Critical priority",
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority"
};

function seedCases(): GovernmentCase[] {
  return [
    {
      id: "GC-001",
      subject: "Dharmagarh NAC",
      status: "under_review",
      priority: "high",
      findings: 1,
      evidence: 16,
      outstanding: 6,
      openedAt: new Date().toISOString(),
      owner: "Unassigned",
      source: "public_handoff"
    },
    {
      id: "GC-002",
      subject: "Procurement review queue",
      status: "open",
      priority: "medium",
      findings: 2,
      evidence: 8,
      outstanding: 3,
      openedAt: new Date().toISOString(),
      owner: "Unassigned",
      source: "internal_review"
    }
  ];
}

function loadCases(): GovernmentCase[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return seedCases();
    const parsed = JSON.parse(raw) as GovernmentCase[];
    return Array.isArray(parsed) && parsed.length ? parsed : seedCases();
  } catch {
    return seedCases();
  }
}

export function GovernmentCaseManagement() {
  const [cases, setCases] = useState<GovernmentCase[]>(() => loadCases());
  const [statusFilter, setStatusFilter] = useState<CaseStatus | "all">("all");
  const [query, setQuery] = useState("");

  const persist = (next: GovernmentCase[]) => {
    setCases(next);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* local-only fallback */ }
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cases.filter((item) => {
      const matchesStatus = statusFilter === "all" || item.status === statusFilter;
      const matchesQuery = !q || `${item.id} ${item.subject} ${item.owner}`.toLowerCase().includes(q);
      return matchesStatus && matchesQuery;
    });
  }, [cases, query, statusFilter]);

  const counts = useMemo(() => {
    return cases.reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = (acc[item.status] ?? 0) + 1;
      return acc;
    }, {});
  }, [cases]);

  function advanceCase(id: string) {
    const order: CaseStatus[] = ["open", "under_review", "evidence_requested", "monitoring", "escalated", "closed"];
    persist(cases.map((item) => {
      if (item.id !== id) return item;
      const currentIndex = order.indexOf(item.status);
      return { ...item, status: order[Math.min(currentIndex + 1, order.length - 1)] };
    }));
  }

  return (
    <div className="space-y-6">
      <Section
        eyebrow="Government workflow"
        title="Case management"
        action={<Chip tone="neutral">Human decision required</Chip>}
      >
        <div className="rounded-xl border border-border bg-surface/60 p-4">
          <div className="grid gap-3 md:grid-cols-6">
            <CaseStat label="Open" value={counts.open ?? 0} />
            <CaseStat label="Under review" value={counts.under_review ?? 0} />
            <CaseStat label="Evidence requested" value={counts.evidence_requested ?? 0} />
            <CaseStat label="Monitoring" value={counts.monitoring ?? 0} />
            <CaseStat label="Escalated" value={counts.escalated ?? 0} />
            <CaseStat label="Closed" value={counts.closed ?? 0} />
          </div>

          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search case ID, subject, owner…"
                className="h-10 w-full rounded-xl border border-border bg-bg-2/50 pl-9 pr-3 text-sm text-text outline-none focus:border-accent/50"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as CaseStatus | "all")}
              className="h-10 rounded-xl border border-border bg-bg-2/50 px-3 text-sm text-text outline-none focus:border-accent/50"
            >
              <option value="all">All statuses</option>
              {(Object.keys(STATUS_META) as CaseStatus[]).map((status) => <option key={status} value={status}>{STATUS_META[status].label}</option>)}
            </select>
          </div>
        </div>
      </Section>

      <Section eyebrow="Review queue" title="Active cases">
        <div className="space-y-3">
          {filtered.map((item) => {
            const meta = STATUS_META[item.status];
            const Icon = meta.icon;
            return (
              <article key={item.id} className="rounded-2xl border border-border bg-surface/70 p-4 transition-colors hover:border-border-strong">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[11px] text-faint">{item.id}</span>
                      <Chip tone={meta.tone}>{meta.label}</Chip>
                      <Chip tone="neutral">{PRIORITY_LABEL[item.priority]}</Chip>
                      {item.source === "public_handoff" && <Chip tone="neutral">Public handoff</Chip>}
                    </div>
                    <h3 className="mt-2 text-sm font-semibold text-text">{item.subject}</h3>
                    <div className="mt-1 text-xs text-muted">Owner: {item.owner}</div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:w-[360px]">
                    <CaseMetric label="Findings" value={item.findings} />
                    <CaseMetric label="Evidence" value={item.evidence} />
                    <CaseMetric label="Open requests" value={item.outstanding} />
                    <div className="hidden sm:block">
                      <CaseMetric label="Next state" value={item.status === "closed" ? "—" : "→"} />
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button href={`/investigate?q=${encodeURIComponent(item.subject)}`} variant="subtle" size="sm">
                      Open investigation
                    </Button>
                    <Button onClick={() => advanceCase(item.id)} disabled={item.status === "closed"} size="sm" icon={<CheckCircle2 className="h-4 w-4" />}>
                      Advance
                    </Button>
                  </div>
                </div>
              </article>
            );
          })}
          {!filtered.length && (
            <div className="rounded-xl border border-dashed border-border bg-surface/40 p-8 text-center text-sm text-faint">No cases match the current filter.</div>
          )}
        </div>
      </Section>

      <div className="rounded-2xl border border-warning/20 bg-warning/[0.04] p-4 text-xs leading-relaxed text-muted">
        <Flag className="mr-1.5 inline h-4 w-4 text-warning" />
        Case status is a human workflow state. Advancing a case does not change SENTRY's deterministic risk assessment, create an enforcement action, or imply a finding has been substantiated.
      </div>

      <div className="text-[11px] text-faint">
        This demo board stores case workflow state locally in the browser. It is a product-surface prototype, not a shared government case-management system.
      </div>
    </div>
  );
}

export function buildGovernmentCaseFromReasoning(reasoning: InvestigationReasoning): GovernmentCase {
  const highest = reasoning.risk_level === "critical" || reasoning.risk_level === "high" ? reasoning.risk_level : "medium";
  return {
    id: `GC-${Date.now()}`,
    subject: reasoning.subject,
    status: "open",
    priority: highest,
    findings: reasoning.findings.length,
    evidence: reasoning.evidence_ledger.length,
    outstanding: reasoning.findings.reduce((total, finding) => total + (finding.required_evidence?.length ?? 0), 0),
    openedAt: new Date().toISOString(),
    owner: "Unassigned",
    source: "public_handoff"
  };
}

function CaseStat({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border border-border bg-bg-2/40 p-2.5"><div className="t-label">{label}</div><div className="mt-1 text-lg font-semibold tabular text-text">{value}</div></div>;
}

function CaseMetric({ label, value }: { label: string; value: number | string }) {
  return <div className="rounded-lg border border-border bg-bg-2/50 px-2.5 py-2 text-center"><div className="t-label">{label}</div><div className="mt-1 text-sm font-semibold tabular text-text">{value}</div></div>;
}
