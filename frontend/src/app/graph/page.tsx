import { Network, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";

import { PageHeader, PageShell } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/states";
import { getRelationshipGraph } from "@/lib/api";
import { RelationshipGraphExplorer } from "./relationship-graph";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    company_id?: string;
    tender_id?: string;
    depth?: string;
  }>;
};

export default async function GraphPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const depth = parseDepth(params.depth);
  const graph = await getRelationshipGraph({
    companyId: params.company_id,
    tenderId: params.tender_id,
    depth
  });

  const focusedLabel = params.company_id
    ? "Focused on supplier"
    : params.tender_id
      ? "Focused on tender"
      : "Portfolio relationship view";

  return (
    <PageShell>
      <PageHeader
        eyebrow="Relationships"
        title="Relationship Investigation"
        subtitle="Trace buyers, suppliers, tenders, awards, indicators, documents and evidence as one connected investigation surface."
        breadcrumb={[{ label: "Dashboard", href: "/" }, { label: "Relationship Investigation" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-bg-2/50 px-3 text-xs text-muted">
              <Network className="h-3.5 w-3.5 text-accent" />
              {focusedLabel}
            </span>
            <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-bg-2/50 px-3 text-xs text-muted">
              <SlidersHorizontal className="h-3.5 w-3.5 text-accent" />
              Depth {depth}
            </span>
            <Link
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong hover:bg-surface-2"
              href="/tenders"
            >
              <Search className="h-4 w-4" />
              Find a tender
            </Link>
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-surface/60 p-2">
        <span className="px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">Investigation radius</span>
        {[1, 2, 3].map((value) => {
          const active = value === depth;
          const query = new URLSearchParams();
          if (params.company_id) query.set("company_id", params.company_id);
          if (params.tender_id) query.set("tender_id", params.tender_id);
          query.set("depth", String(value));
          return (
            <Link
              key={value}
              href={`/graph?${query.toString()}`}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${active ? "border-accent/45 bg-accent/10 text-accent" : "border-border bg-bg-2/50 text-muted hover:text-text"}`}
            >
              {value === 1 ? "Direct" : value === 2 ? "Connected" : "Extended"}
            </Link>
          );
        })}
        <span className="ml-auto hidden text-[10.5px] text-faint md:block">Use filters and node search inside the graph to narrow the investigation.</span>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <ContextStat label="Nodes" value={graph.nodes.length} detail="Entities in view" />
        <ContextStat label="Relationships" value={graph.edges.length} detail="Connected records" />
        <ContextStat label="Depth" value={depth} detail="Investigation radius" />
        <ContextStat label="Indicators" value={graph.nodes.filter((node) => node.type === "indicator").length} detail="Screening nodes" />
      </div>

      <section className="w-full">
        {graph.nodes.length === 0 ? (
          <EmptyState
            title="No relationships in scope"
            message="SENTRY could not find connected procurement records for this view. Start from a verified supplier or tender to build a focused investigation graph."
            suggestions={[
              "Open the Investigation Workspace and select a canonical entity",
              "Search tender records and open a relationship view",
              "Connect the CPPP or GeM source connector in Settings"
            ]}
          />
        ) : (
          <RelationshipGraphExplorer
            graph={graph}
            title="Connected procurement evidence"
            subtitle="Select a node or relationship to inspect the underlying record and provenance."
          />
        )}
      </section>
    </PageShell>
  );
}

function ContextStat({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface/70 px-4 py-3 elevate">
      <div className="t-label">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular text-text">{value.toLocaleString("en-IN")}</div>
      <div className="mt-1 text-[11px] text-faint">{detail}</div>
    </div>
  );
}

function parseDepth(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 3) {
    return 2;
  }
  return parsed;
}
