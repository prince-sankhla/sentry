import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Building2, Calendar, GitBranch, ShieldAlert } from "lucide-react";

import { PageHeader, PageShell, SeverityBadge } from "@/components/ui/page";
import { Section, SurfaceCard } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Timeline } from "@/components/ui/timeline";
import { PdfIntelligence } from "@/components/intel/pdf-intelligence";
import { getTender, type ProcurementIntelligenceSignal } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{
    tenderId: string;
  }>;
};

export default async function TenderDetailPage({ params }: PageProps) {
  const { tenderId } = await params;
  const tender = await getTender(tenderId).catch((error) => {
    if (error instanceof Error && error.message === "not_found") {
      notFound();
    }
    throw error;
  });

  const timelineItems = [
    { label: "Published", value: formatDate(tender.published_date), detail: tender.reference_number },
    { label: "Closing", value: formatDate(tender.closing_date) },
    { label: "Record updated", value: formatDate(tender.updated_at) }
  ];

  return (
    <PageShell>
      <PageHeader
        eyebrow="Tender File"
        title={tender.title}
        subtitle={<span className="font-mono text-faint">{tender.reference_number}</span>}
        breadcrumb={[
          { label: "Dashboard", href: "/" },
          { label: "Tenders", href: "/tenders" },
          { label: tender.reference_number }
        ]}
        actions={
          <Link
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-text transition hover:border-border-strong"
            href={`/graph?tender_id=${tenderId}&depth=2`}
          >
            <GitBranch className="h-4 w-4" aria-hidden="true" />
            Open graph
          </Link>
        }
      />

      <section className="grid w-full gap-5 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <Section eyebrow="Overview" title="Tender Details">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Procuring entity" value={tender.buyer.name ?? tender.procuring_entity ?? "Unknown"} />
              <Detail label="Published date" value={formatDate(tender.published_date)} />
              <Detail label="Estimated value" value={`${formatMoney(tender.estimated_value, tender.currency)} ${tender.currency}`} />
              <Detail label="Currency" value={tender.currency} />
            </dl>
            {tender.description ? <p className="mt-5 text-sm leading-6 text-muted">{tender.description}</p> : null}
          </Section>

          <Section eyebrow="Outcome" title="Awards">
            {tender.awards.length === 0 ? (
              <EmptyState message="No awards recorded for this tender." />
            ) : (
              <div className="space-y-3">
                {tender.awards.map((award) => (
                  <div className="grid gap-3 rounded-[16px] border border-border bg-bg-2 p-4 transition hover:bg-surface-2 md:grid-cols-[1fr_auto]" key={award.id}>
                    <div>
                      <Link className="flex items-center gap-2 text-sm font-semibold text-text transition hover:text-accent" href={`/companies/${award.company.id}`}>
                        <Award className="h-4 w-4 text-accent" aria-hidden="true" />
                        {award.company.name}
                      </Link>
                      <div className="mt-1 font-mono text-xs text-faint">{award.company.registration_number ?? "No identifier"}</div>
                    </div>
                    <div className="text-left md:text-right">
                      <div className="text-sm font-semibold tabular-nums text-text">
                        {formatMoney(award.award_value, award.currency)} {award.currency}
                      </div>
                      <div className="mt-1 text-xs text-muted">{formatDate(award.award_date)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section eyebrow="Phase 1" title="Procurement Intelligence">
            <IntelligenceSignals signals={tender.intelligence.signals} />
          </Section>

          {tender.pdf_intelligence && !tender.pdf_intelligence.empty ? (
            <Section eyebrow="Document" title="PDF Intelligence">
              <PdfIntelligence extraction={tender.pdf_intelligence} />
            </Section>
          ) : null}

          <Section eyebrow="Evidence" title="Evidence Placeholder">
            <EmptyState title="No evidence attached" message="Supporting documents and analyst evidence can be attached here when available." />
          </Section>
        </div>

        <aside className="space-y-5 lg:self-start">
          <SurfaceCard className="p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-text">
              <Calendar className="h-4 w-4 text-accent" aria-hidden="true" />
              Timeline
            </div>
            <div className="mt-4">
              <Timeline items={timelineItems} />
            </div>
          </SurfaceCard>

          <Section eyebrow="Entities" title="Related Companies">
            {tender.participating_companies.length === 0 ? (
              <EmptyState message="No companies recorded." />
            ) : (
              <div className="space-y-3">
                {tender.participating_companies.map((company) => (
                  <Link
                    className="block rounded-[16px] border border-border bg-bg-2 p-3 transition hover:border-border-strong hover:bg-surface-2"
                    href={`/companies/${company.id}`}
                    key={company.id}
                  >
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                      <Building2 className="h-4 w-4 text-accent" aria-hidden="true" />
                      {company.name}
                    </div>
                    <div className="mt-1 font-mono text-xs text-faint">{company.registration_number ?? "No identifier"}</div>
                  </Link>
                ))}
              </div>
            )}
          </Section>

          <Section eyebrow="Scoring" title="Buyer-Supplier Scores">
            {tender.intelligence.relationship_scores.length === 0 ? (
              <EmptyState message="No relationship score is available for this tender." />
            ) : (
              <div className="space-y-3">
                {tender.intelligence.relationship_scores.map((relationship) => (
                  <div className="rounded-[16px] border border-border bg-bg-2 p-3" key={`${relationship.buyer}-${relationship.supplier_id}`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-text">{relationship.supplier_name}</div>
                        <div className="mt-1 text-xs text-muted">{relationship.buyer ?? "Unknown buyer"}</div>
                      </div>
                      <div className="text-lg font-semibold tabular-nums text-accent">{relationship.score}</div>
                    </div>
                    <div className="mt-2 text-xs text-muted">
                      {relationship.awards_to_supplier} of {relationship.total_buyer_awards} buyer awards
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </aside>
      </section>
    </PageShell>
  );
}

function IntelligenceSignals({ signals }: { signals: ProcurementIntelligenceSignal[] }) {
  if (signals.length === 0) {
    return <EmptyState message="No Phase 1 procurement intelligence signals were detected." />;
  }

  return (
    <div className="grid gap-3">
      {signals.map((signal) => (
        <div className="rounded-[16px] border border-border bg-bg-2 p-4" key={`${signal.type}-${signal.company_id}-${signal.buyer}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-text">
                <ShieldAlert className="h-4 w-4 text-accent" aria-hidden="true" />
                {signal.title}
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{signal.summary}</p>
            </div>
            <SeverityBadge severity={signal.severity} score={signal.score} />
          </div>
          {signal.evidence.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {signal.evidence.map((item, index) => (
                <span
                  className="rounded-md border border-border bg-bg-2 px-2 py-1 text-[11px] text-muted"
                  key={`${item}-${index}`}
                >
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-border bg-bg-2 p-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-faint">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-text">{value}</dd>
    </div>
  );
}
