"use client";

import { ExternalLink, Globe2, Landmark, Newspaper, ShieldCheck } from "lucide-react";
import { Section } from "@/components/ui/card";
import { Chip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/states";
import { formatDate } from "@/lib/format";

export type WebContextIntelligenceItem = {
  id: string;
  source: string;
  source_type: string;
  evidence_type: string;
  cluster: string;
  confidence: number;
  confidence_tier: string;
  publication_date: string | null;
  url: string;
  citation: string;
  evidence_summary: string;
  related_entities: string[];
  related_tenders: string[];
  related_contracts: string[];
  related_organizations: string[];
  related_investigations: string[];
  matched_terms: string[];
  retrieved_at: string;
};

export type WebContextIntelligenceData = {
  query: string;
  total_items: number;
  clusters: Array<{ cluster: string; label: string; count: number; items: WebContextIntelligenceItem[] }>;
};

type Props = { data: WebContextIntelligenceData | null };

const iconForCluster: Record<string, typeof Globe2> = {
  news: Newspaper,
  government: Landmark,
  contracts: ShieldCheck,
};

export function WebContextIntelligence({ data }: Props) {
  const items = data?.clusters.flatMap((cluster) => cluster.items) ?? [];

  return (
    <Section
      eyebrow="Open-source context"
      title="Web intelligence — context, not proof"
      action={<Chip tone="neutral">{data?.total_items ?? 0} contextual sources</Chip>}
    >
      <div className="rounded-xl border border-accent/20 bg-accent/[0.04] px-4 py-3 text-[11.5px] leading-relaxed text-muted">
        <span className="font-semibold text-text">How SENTRY uses the web:</span> current tender and contract pages may corroborate procurement facts. News, historical coverage, audit, litigation and other public context stay in this separate layer and never alter the deterministic risk assessment.
      </div>

      {!items.length ? (
        <div className="mt-4">
          <EmptyState
            icon={<Globe2 className="h-5 w-5" />}
            title="No contextual web sources captured"
            message="SENTRY searched the open web, but no admissible contextual pages were retained for this subject yet."
          />
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          {data?.clusters.map((cluster) => {
            const Icon = iconForCluster[cluster.cluster] ?? Globe2;
            return (
              <div key={cluster.cluster} className="rounded-2xl border border-border bg-bg-2/30 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="grid h-8 w-8 place-items-center rounded-lg border border-border bg-surface text-accent">
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div>
                      <div className="text-[13px] font-semibold text-text">{cluster.label}</div>
                      <div className="text-[10.5px] text-faint">{cluster.count} source{cluster.count === 1 ? "" : "s"} · supplementary context</div>
                    </div>
                  </div>
                  <span className="rounded-full border border-border bg-surface px-2 py-1 text-[9px] font-semibold uppercase tracking-wide text-faint">Not risk evidence</span>
                </div>

                <div className="mt-3 grid gap-2.5 lg:grid-cols-2">
                  {cluster.items.slice(0, 6).map((item) => (
                    <article key={item.id} className="rounded-xl border border-border bg-surface/70 p-3.5 transition hover:border-border-strong">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="line-clamp-2 text-[13px] font-medium leading-snug text-text">{item.evidence_summary}</div>
                          <div className="mt-1 truncate text-[10.5px] text-faint">{item.source} · {item.publication_date ? formatDate(item.publication_date) : formatDate(item.retrieved_at)}</div>
                        </div>
                        <span className="shrink-0 rounded-md border border-border bg-bg-2 px-1.5 py-1 text-[9px] font-semibold uppercase tracking-wide text-faint">{item.confidence_tier}</span>
                      </div>
                      <p className="mt-2 line-clamp-2 text-[11.5px] leading-relaxed text-muted">{item.citation}</p>
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className="font-mono text-[9.5px] text-faint">Captured snapshot · {item.id.slice(0, 8)}…</span>
                        <div className="flex items-center gap-1.5">
                          <a href={`/api/web/archive/${encodeURIComponent(item.id)}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-success/25 bg-success/[0.06] px-2 py-1.5 text-[10.5px] font-semibold text-success hover:bg-success/10">
                            <ShieldCheck className="h-3 w-3" /> Snapshot
                          </a>
                          <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/60 px-2 py-1.5 text-[10.5px] text-muted hover:border-accent/35 hover:text-accent">
                            <ExternalLink className="h-3 w-3" /> Live source
                          </a>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Section>
  );
}
