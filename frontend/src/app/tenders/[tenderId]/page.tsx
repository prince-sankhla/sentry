import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Building2, Calendar, GitBranch, ShieldAlert } from "lucide-react";

import { Section, SurfaceCard } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Timeline } from "@/components/ui/timeline";
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
    <main className="min-h-screen bg-[#FAF8F5] text-[#333333]">
      <section className="border-b border-[#E8D8B1] bg-white/95 backdrop-blur">
        <div className="mx-auto w-full max-w-[1600px] px-6 py-6 lg:px-8">
          <nav className="text-xs text-[#6B7280]">
            <Link className="hover:text-[#2F2F2F]" href="/">
              Dashboard
            </Link>
            <span className="px-2">/</span>
            <Link className="hover:text-[#2F2F2F]" href="/tenders">
              Tenders
            </Link>
            <span className="px-2">/</span>
            <span>{tender.reference_number}</span>
          </nav>
          <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-4xl">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#B88927]">Tender File</p>
              <h1 className="mt-2 text-2xl font-semibold leading-tight text-[#2F2F2F] sm:text-3xl">{tender.title}</h1>
              <p className="mt-2 text-sm text-[#6B7280]">{tender.reference_number}</p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[16px] border border-[#E8D8B1] bg-white px-4 text-sm font-semibold text-[#2F2F2F] transition hover:border-[#D4A74B] hover:shadow-[0_16px_36px_rgba(87,63,14,0.08)]"
              href={`/graph?tender_id=${tenderId}&depth=2`}
            >
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              Open graph
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1600px] gap-5 px-6 py-6 lg:grid-cols-[1fr_360px] lg:px-8">
        <div className="space-y-5">
          <Section eyebrow="Overview" title="Tender Details">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Procuring entity" value={tender.buyer.name ?? tender.procuring_entity ?? "Unknown"} />
              <Detail label="Published date" value={formatDate(tender.published_date)} />
              <Detail label="Estimated value" value={`${formatMoney(tender.estimated_value, tender.currency)} ${tender.currency}`} />
              <Detail label="Currency" value={tender.currency} />
            </dl>
            {tender.description ? <p className="mt-5 text-sm leading-6 text-[#4B5563]">{tender.description}</p> : null}
          </Section>

          <Section eyebrow="Outcome" title="Awards">
            {tender.awards.length === 0 ? (
              <EmptyState message="No awards recorded for this tender." />
            ) : (
              <div className="space-y-3">
                {tender.awards.map((award) => (
                  <div className="grid gap-3 rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-4 md:grid-cols-[1fr_auto]" key={award.id}>
                    <div>
                      <Link className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F] hover:text-[#1E3A8A]" href={`/companies/${award.company.id}`}>
                        <Award className="h-4 w-4 text-[#D97706]" aria-hidden="true" />
                        {award.company.name}
                      </Link>
                      <div className="mt-1 text-xs text-[#6B7280]">{award.company.registration_number ?? "No identifier"}</div>
                    </div>
                    <div className="text-left md:text-right">
                      <div className="text-sm font-semibold tabular-nums text-[#2F2F2F]">
                        {formatMoney(award.award_value, award.currency)} {award.currency}
                      </div>
                      <div className="mt-1 text-xs text-[#6B7280]">{formatDate(award.award_date)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section eyebrow="Phase 1" title="Procurement Intelligence">
            <IntelligenceSignals signals={tender.intelligence.signals} />
          </Section>

          <Section eyebrow="Evidence" title="Evidence Placeholder">
            <EmptyState title="No evidence attached" message="Supporting documents and analyst evidence can be attached here when available." />
          </Section>
        </div>

        <aside className="space-y-5 lg:self-start">
          <SurfaceCard className="p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F]">
              <Calendar className="h-4 w-4 text-[#B88927]" aria-hidden="true" />
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
                    className="block rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-3 transition hover:border-[#D4A74B] hover:shadow-[0_14px_32px_rgba(87,63,14,0.06)]"
                    href={`/companies/${company.id}`}
                    key={company.id}
                  >
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F]">
                      <Building2 className="h-4 w-4 text-[#1E3A8A]" aria-hidden="true" />
                      {company.name}
                    </div>
                    <div className="mt-1 text-xs text-[#6B7280]">{company.registration_number ?? "No identifier"}</div>
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
                  <div className="rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-3" key={`${relationship.buyer}-${relationship.supplier_id}`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-[#2F2F2F]">{relationship.supplier_name}</div>
                        <div className="mt-1 text-xs text-[#6B7280]">{relationship.buyer ?? "Unknown buyer"}</div>
                      </div>
                      <div className="text-lg font-semibold tabular-nums text-[#8A6412]">{relationship.score}</div>
                    </div>
                    <div className="mt-2 text-xs text-[#6B7280]">
                      {relationship.awards_to_supplier} of {relationship.total_buyer_awards} buyer awards
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </aside>
      </section>
    </main>
  );
}

function IntelligenceSignals({ signals }: { signals: ProcurementIntelligenceSignal[] }) {
  if (signals.length === 0) {
    return <EmptyState message="No Phase 1 procurement intelligence signals were detected." />;
  }

  return (
    <div className="grid gap-3">
      {signals.map((signal) => (
        <div className="rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-4" key={`${signal.type}-${signal.company_id}-${signal.buyer}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#2F2F2F]">
                <ShieldAlert className="h-4 w-4 text-[#D97706]" aria-hidden="true" />
                {signal.title}
              </div>
              <p className="mt-2 text-sm leading-6 text-[#4B5563]">{signal.summary}</p>
            </div>
            <span className="rounded-[12px] border border-[#D4A74B] bg-[#FFF5DD] px-2 py-1 text-xs font-semibold uppercase text-[#8A6412]">
              {signal.severity}
            </span>
          </div>
          <div className="mt-3 text-xs text-[#6B7280]">{signal.evidence.join(" | ")}</div>
        </div>
      ))}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-[#E8D8B1] bg-[#FFFDF8] p-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6B7280]">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-[#2F2F2F]">{value}</dd>
    </div>
  );
}
