import { Award, Building2, FileText } from "lucide-react";
import Link from "next/link";
import { getDashboardRecent } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { Section } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { InvestigateAction } from "@/components/intel/investigate-action";
import { formatDate, formatMoneyFull } from "@/lib/format";
import { InvestigationLauncher } from "./investigation-launcher";
import { LiveTenderIngestion } from "./live-tender-ingestion";

export const dynamic = "force-dynamic";

export default async function InvestigationsPage() {
  let recent;
  try {
    recent = await getDashboardRecent(6);
  } catch {
    recent = { latest_tenders: [], latest_awarded_companies: [], latest_awards: [] };
  }

  const suggestions = Array.from(
    new Set([
      ...recent.latest_tenders.map((t) => t.procuring_entity),
      ...recent.latest_awarded_companies.map((c) => c.name)
    ].filter((s): s is string => Boolean(s)))
  ).slice(0, 4);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Intelligence"
        title="Investigations"
        subtitle="Launch a new intelligence workflow or jump directly from any tender, supplier, or award."
      />

      <LiveTenderIngestion />
      <InvestigationLauncher suggestions={suggestions} />

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Section eyebrow="Entry points" title="Latest tenders" action={<Link href="/tenders" className="text-xs text-accent hover:underline">All →</Link>}>
          {recent.latest_tenders.length === 0 ? <EmptyState message="No tenders imported yet." /> : (
            <ul className="space-y-2">
              {recent.latest_tenders.map((t) => (
                <li key={t.id} className="flex items-center gap-2 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2">
                  <Link href={`/tenders/${t.id}`} className="flex min-w-0 flex-1 items-start gap-3">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-info" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm text-text">{t.title}</span>
                      <span className="block truncate text-xs text-faint">{t.procuring_entity ?? "Unknown buyer"} · {formatMoneyFull(t.estimated_value, t.currency)}</span>
                    </span>
                  </Link>
                  <InvestigateAction query={t.procuring_entity ?? t.title} size="sm" label="Investigate" variant="subtle" />
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section eyebrow="Entry points" title="Recent suppliers" action={<Link href="/companies" className="text-xs text-accent hover:underline">All →</Link>}>
          {recent.latest_awarded_companies.length === 0 ? <EmptyState message="No companies imported yet." /> : (
            <ul className="space-y-2">
              {recent.latest_awarded_companies.map((c) => (
                <li key={c.id} className="flex items-center gap-2 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2">
                  <Link href={`/companies/${c.id}`} className="flex min-w-0 flex-1 items-start gap-3">
                    <Building2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm text-text">{c.name}</span>
                      <span className="block truncate font-mono text-xs text-faint">{c.registration_number ?? "No registration"}</span>
                    </span>
                  </Link>
                  <InvestigateAction query={c.name} size="sm" label="Investigate" variant="subtle" />
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section eyebrow="Entry points" title="Recent awards" action={<Link href="/awards" className="text-xs text-accent hover:underline">All →</Link>}>
          {recent.latest_awards.length === 0 ? <EmptyState message="No awards imported yet." /> : (
            <ul className="space-y-2">
              {recent.latest_awards.map((a) => (
                <li key={a.id} className="flex items-center gap-2 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2">
                  <Link href={`/companies/${a.company.id}`} className="flex min-w-0 flex-1 items-start gap-3">
                    <Award className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm text-text">{a.company.name}</span>
                      <span className="block truncate text-xs text-faint">{formatMoneyFull(a.award_value, a.currency)} · {formatDate(a.award_date)}</span>
                    </span>
                  </Link>
                  <InvestigateAction query={a.company.name} size="sm" label="Investigate" variant="subtle" />
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </PageShell>
  );
}
