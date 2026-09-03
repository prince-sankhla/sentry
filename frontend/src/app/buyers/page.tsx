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
        title="Buyer Kundali"
        subtitle="Understand a procuring entity across its tender volume, suppliers, methods, value patterns, timelines, and review leads."
        breadcrumb={[
          { label: "Dashboard", href: "/" },
          { label: "Buyer Kundali" }
        ]}
        actions={
          <Link
            href="/investigations"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong"
          >
            Open investigation desk
            <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      <SurfaceCard className="mb-5 overflow-hidden p-5 md:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-accent">
              <Building2 className="h-4 w-4" />
              Buyer profile
            </div>
            <div className="mt-2 text-sm text-muted">
              Search the exact procuring-entity name currently stored in Indian tender records.
            </div>
          </div>
          <form className="flex w-full max-w-2xl gap-2" action="/buyers">
            <input
              name="name"
              defaultValue={buyer}
              placeholder="e.g. National Highways Authority of India"
              className="h-11 min-w-0 flex-1 rounded-xl border border-border bg-bg-2 px-4 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/50"
            />
            <button className="h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-bg transition hover:brightness-110" type="submit">
              Load buyer
            </button>
          </form>
        </div>
      </SurfaceCard>

      {buyer ? <BuyerKundaliPanel buyer={buyer} /> : (
        <SurfaceCard className="p-10 text-center">
          <Building2 className="mx-auto h-10 w-10 text-accent/60" />
          <div className="mt-4 text-lg font-semibold text-text">Choose a buyer to inspect</div>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
            The Buyer Kundali is built from indexed Indian tender records and keeps bidder-level or cancellation claims as insufficient-data when the source does not expose them.
          </p>
        </SurfaceCard>
      )}
    </PageShell>
  );
}
