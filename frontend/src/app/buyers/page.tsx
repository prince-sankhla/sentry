import Link from "next/link";
import { ArrowRight, Building2 } from "lucide-react";

import { PageHeader, PageShell } from "@/components/ui/page";
import { SurfaceCard } from "@/components/ui/card";
import { BuyerKundaliPanel } from "./buyer-kundali-panel";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{ name?: string }>;
};

export default async function BuyersPage({ searchParams }: Props) {
  const params = await searchParams;
  const buyer = (params.name ?? "").trim();

  return (
    <PageShell>
      <PageHeader
        eyebrow="Buyer Intelligence"
        title="Buyer Intelligence Profile"
        subtitle="Review a procuring entity across tender activity, supplier relationships, procurement methods, value patterns, timelines, and evidence-backed review leads."
        breadcrumb={[
          { label: "Command Center", href: "/" },
          { label: "Buyer Intelligence" }
        ]}
        actions={
          <Link
            href="/investigations"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong"
          >
            Open investigation workspace
            <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      <SurfaceCard className="mb-5 overflow-hidden p-5 md:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-accent">
              <Building2 className="h-4 w-4" />
              Procuring-entity lookup
            </div>
            <div className="mt-2 max-w-xl text-sm leading-6 text-muted">
              Search the procuring-entity name as recorded in the indexed Indian tender records. Use the verified entity name for consistent cross-record analysis.
            </div>
          </div>
          <form className="flex w-full max-w-2xl gap-2" action="/buyers">
            <label className="sr-only" htmlFor="buyer-name">Procuring-entity name</label>
            <input
              id="buyer-name"
              name="name"
              defaultValue={buyer}
              placeholder="e.g. National Highways Authority of India"
              className="h-11 min-w-0 flex-1 rounded-xl border border-border bg-bg-2 px-4 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/50 focus:ring-4 focus:ring-accent/10"
            />
            <button className="h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-bg transition hover:brightness-110" type="submit">
              View profile
            </button>
          </form>
        </div>
      </SurfaceCard>

      {buyer ? <BuyerKundaliPanel buyer={buyer} /> : (
        <SurfaceCard className="p-10 text-center">
          <Building2 className="mx-auto h-10 w-10 text-accent/60" />
          <div className="mt-4 text-lg font-semibold text-text">Select a procuring entity</div>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
            The profile is built from indexed Indian tender records. Bidder participation, cancellation status, or other facts are not inferred when the source does not provide them.
          </p>
        </SurfaceCard>
      )}
    </PageShell>
  );
}
