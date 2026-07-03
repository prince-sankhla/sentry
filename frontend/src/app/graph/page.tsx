import Link from "next/link";

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
    <main className="min-h-screen bg-[#FAF8F5] text-[#333333]">
      <section className="border-b border-[#E8D8B1] bg-white/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-4 px-6 py-6 lg:px-8">
          <nav className="text-xs text-[#6B7280]">
            <Link className="hover:text-[#2F2F2F]" href="/">
              Dashboard
            </Link>
            <span className="px-2">/</span>
            <span>Investigation Graph</span>
          </nav>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#B88927]">SENTRY Graph Engine</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#2F2F2F]">Graph Investigation</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[#6B7280]">
                Explore companies, tenders, awards, buyers, evidence, and procurement indicators as an interactive investigation graph.
              </p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-[16px] border border-[#E8D8B1] bg-white px-4 text-sm font-semibold text-[#2F2F2F] transition hover:border-[#D4A74B] hover:shadow-[0_16px_36px_rgba(87,63,14,0.08)]"
              href="/tenders"
            >
              Search tenders
            </Link>
          </div>
        </div>
      </section>
      <section className="mx-auto w-full max-w-[1600px] px-6 py-5 lg:px-8">
        {graph.nodes.length === 0 ? (
          <div className="rounded-[16px] border border-dashed border-[#E8D8B1] bg-white p-8 text-center text-sm text-[#6B7280]">
            No relationships are available yet. Import tenders and awards to populate the graph.
          </div>
        ) : (
          <RelationshipGraphExplorer graph={graph} />
        )}
      </section>
    </main>
  );
}

function parseDepth(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 3) {
    return 2;
  }
  return parsed;
}
