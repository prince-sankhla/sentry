import Link from "next/link";
import { ArrowRight, Building2, Search, ShieldAlert } from "lucide-react";

import { PageHeader, PageShell } from "@/components/ui/page";
import { SurfaceCard } from "@/components/ui/card";
import { BuyerKundaliPanel } from "./buyer-kundali-panel";
import { InvestigateAction } from "@/components/intel/investigate-action";

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
        eyebrow="Entity Intelligence"
        title="Buyer intelligence"
        subtitle="Understand how a procuring entity buys: tender activity, supplier relationships, procurement methods, value patterns, timelines, and source-backed review signals."
        breadcrumb={[
          { label: "Command Center", href: "/" },
          { label: "Buyer Intelligence" }
        ]}
        actions={
          buyer ? (
            <div className="flex flex-wrap gap-2">
              <InvestigateAction query={buyer} label="Investigate buyer" variant="primary" />
              <Link
                href="/investigations"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong hover:bg-surface-2"
              >
                Investigation workspace
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            <Link
              href="/investigations"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong hover:bg-surface-2"
            >
              Start investigation
              <ArrowRight className="h-4 w-4" />
            </Link>
          )
        }
      />

      <SurfaceCard className="mb-5 overflow-hidden">
        <div className="border-b border-border bg-bg-2/30 px-5 py-4 md:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-accent">
              <Search className="h-3.5 w-3.5" />
              Find a procuring entity
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-[10px] font-medium text-faint">
              <ShieldAlert className="h-3 w-3" />
              Review signals are not determinations
            </span>
          </div>
        </div>

        <div className="p-5 md:p-6">
          <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <div className="text-sm font-medium text-text">Use the recorded entity name</div>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
                Search the procuring-entity name exactly as it appears in indexed Indian tender records so SENTRY can keep the profile consistent across sources.
              </p>
            </div>
            <form className="flex w-full gap-2 lg:max-w-2xl" action="/buyers">
              <label className="sr-only" htmlFor="buyer-name">Procuring-entity name</label>
              <input
                id="buyer-name"
                name="name"
                defaultValue={buyer}
                placeholder="e.g. National Highways Authority of India"
                className="h-11 min-w-0 flex-1 rounded-xl border border-border bg-bg-2 px-4 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/50 focus:ring-4 focus:ring-accent/10"
              />
              <button className="inline-flex h-11 items-center gap-2 rounded-xl bg-accent px-5 text-sm font-semibold text-bg transition hover:brightness-110" type="submit">
                <Search className="h-4 w-4" />
                View profile
              </button>
            </form>
          </div>
        </div>
      </SurfaceCard>

      {buyer ? (
        <BuyerKundaliPanel buyer={buyer} />
      ) : (
        <SurfaceCard className="p-10 text-center md:p-14">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl border border-accent/25 bg-accent/[0.08] text-accent">
            <Building2 className="h-5 w-5" />
          </span>
          <div className="mt-4 text-lg font-semibold text-text">Select a procuring entity</div>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
            SENTRY will build the profile from indexed Indian tender records. Where source data does not expose bidder participation, cancellations, or other facts, the profile reports those fields as unavailable rather than inferring them.
          </p>
        </SurfaceCard>
      )}
    </PageShell>
  );
}
