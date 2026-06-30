import Link from "next/link";
import { notFound } from "next/navigation";
import { Award, Building2, Calendar, GitBranch } from "lucide-react";

import { Section, SurfaceCard } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { Timeline } from "@/components/ui/timeline";
import { getTender } from "@/lib/api";
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
    <main className="min-h-screen bg-[#0B0F14]">
      <section className="border-b border-[#2A3441] bg-[#121821]">
        <div className="mx-auto w-full max-w-7xl px-5 py-7 sm:px-8">
          <nav className="text-xs text-[#9AA4AF]">
            <Link className="hover:text-[#E6E8EB]" href="/">
              Dashboard
            </Link>
            <span className="px-2">/</span>
            <Link className="hover:text-[#E6E8EB]" href="/tenders">
              Tenders
            </Link>
            <span className="px-2">/</span>
            <span>{tender.reference_number}</span>
          </nav>
          <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-4xl">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#C58B2A]">Tender File</p>
              <h1 className="mt-2 text-2xl font-semibold leading-tight text-[#E6E8EB] sm:text-3xl">{tender.title}</h1>
              <p className="mt-2 text-sm text-[#9AA4AF]">{tender.reference_number}</p>
            </div>
            <Link
              className="inline-flex h-10 items-center justify-center gap-2 rounded-[4px] border border-[#2A3441] bg-[#171F2A] px-4 text-sm font-semibold text-[#E6E8EB] transition hover:border-[#C58B2A]"
              href={`/graph?tender_id=${tenderId}&depth=2`}
            >
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              Open graph
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-5 px-5 py-6 sm:px-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <Section eyebrow="Overview" title="Tender Details">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Procuring entity" value={tender.buyer.name ?? tender.procuring_entity ?? "Unknown"} />
              <Detail label="Published date" value={formatDate(tender.published_date)} />
              <Detail label="Estimated value" value={`${formatMoney(tender.estimated_value, tender.currency)} ${tender.currency}`} />
              <Detail label="Currency" value={tender.currency} />
            </dl>
            {tender.description ? <p className="mt-5 text-sm leading-6 text-[#C8CDD3]">{tender.description}</p> : null}
          </Section>

          <Section eyebrow="Outcome" title="Awards">
            {tender.awards.length === 0 ? (
              <EmptyState message="No awards recorded for this tender." />
            ) : (
              <div className="space-y-3">
                {tender.awards.map((award) => (
                  <div className="grid gap-3 rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-4 md:grid-cols-[1fr_auto]" key={award.id}>
                    <div>
                      <Link className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB] hover:text-[#F3D59A]" href={`/companies/${award.company.id}`}>
                        <Award className="h-4 w-4 text-[#C58B2A]" aria-hidden="true" />
                        {award.company.name}
                      </Link>
                      <div className="mt-1 text-xs text-[#9AA4AF]">{award.company.registration_number ?? "No identifier"}</div>
                    </div>
                    <div className="text-left md:text-right">
                      <div className="text-sm font-semibold tabular-nums text-[#E6E8EB]">
                        {formatMoney(award.award_value, award.currency)} {award.currency}
                      </div>
                      <div className="mt-1 text-xs text-[#9AA4AF]">{formatDate(award.award_date)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section eyebrow="Evidence" title="Evidence Placeholder">
            <EmptyState title="No evidence attached" message="Supporting documents and analyst evidence can be attached here when available." />
          </Section>
        </div>

        <aside className="space-y-5 lg:self-start">
          <SurfaceCard className="p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB]">
              <Calendar className="h-4 w-4 text-[#C58B2A]" aria-hidden="true" />
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
                    className="block rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3 transition hover:border-[#C58B2A]"
                    href={`/companies/${company.id}`}
                    key={company.id}
                  >
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#E6E8EB]">
                      <Building2 className="h-4 w-4 text-[#667A52]" aria-hidden="true" />
                      {company.name}
                    </div>
                    <div className="mt-1 text-xs text-[#9AA4AF]">{company.registration_number ?? "No identifier"}</div>
                  </Link>
                ))}
              </div>
            )}
          </Section>
        </aside>
      </section>
    </main>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[4px] border border-[#2A3441] bg-[#171F2A] p-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9AA4AF]">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-[#E6E8EB]">{value}</dd>
    </div>
  );
}
