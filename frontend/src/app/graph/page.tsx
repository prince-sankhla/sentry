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
    <main className="min-h-screen bg-[#0B0F14] text-[#E6E8EB]">
      <section className="border-b border-[#2A3441] bg-[#121821]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-6 sm:px-8">
          <nav className="text-xs text-[#9AA4AF]">
            <Link className="hover:text-[#E6E8EB]" href="/">
              Dashboard
            </Link>
            <span className="px-2">/</span>
            <span>Investigation Graph</span>
          </nav>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#C58B2A]">SENTRY Graph Engine</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#E6E8EB]">Graph Investigation</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[#9AA4AF]">
                Explore companies, tenders, awards, buyers, evidence, and procurement indicators as an interactive investigation graph.
              </p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center rounded-[4px] border border-[#2A3441] bg-[#171F2A] px-4 text-sm font-semibold text-[#E6E8EB] transition hover:border-[#C58B2A]"
              href="/tenders"
            >
              Search tenders
            </Link>
          </div>
        </div>
      </section>
      <section className="mx-auto w-full max-w-7xl px-5 py-5 sm:px-8">
        {graph.nodes.length === 0 ? (
          <div className="rounded-[6px] border border-dashed border-[#2A3441] bg-[#121821] p-8 text-center text-sm text-[#9AA4AF]">
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
