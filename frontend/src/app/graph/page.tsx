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

  return (
    <PageShell>
      <PageHeader
        eyebrow="SENTRY Graph Engine"
        title="Graph Investigation"
        subtitle="Explore companies, tenders, awards, buyers, evidence, and procurement indicators as an interactive investigation graph."
        breadcrumb={[{ label: "Dashboard", href: "/" }, { label: "Investigation Graph" }]}
        actions={
          <Link
            className="inline-flex h-10 items-center justify-center rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong"
            href="/tenders"
          >
            Search tenders
          </Link>
        }
      />
      <section className="w-full">
        {graph.nodes.length === 0 ? (
          <EmptyState
            title="No relationships yet"
            message="Import tenders and awards to populate the investigation graph."
          />
        ) : (
          <RelationshipGraphExplorer graph={graph} />
        )}
      </section>
    </PageShell>
  );
}

function parseDepth(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 3) {
    return 2;
  }
  return parsed;
}
