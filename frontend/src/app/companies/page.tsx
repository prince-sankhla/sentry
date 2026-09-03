import Link from "next/link";
import { Building2, ArrowUpRight } from "lucide-react";
import { getCompanies } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { ListControls } from "@/components/ui/list-controls";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { InvestigateAction } from "@/components/intel/investigate-action";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function CompaniesPage({
  searchParams
}: {
  searchParams: Promise<{ q?: string; offset?: string }>;
}) {
  const sp = await searchParams;
  const q = sp.q?.trim() || undefined;
  const limit = 24;
  const offset = Math.max(0, Number(sp.offset ?? 0) || 0);

  let data;
  try {
    data = await getCompanies({ limit, offset, q });
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Records" title="Companies" />
        <ErrorState message="Could not reach the companies service." />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="Records"
        title="Companies"
        subtitle={`${data.pagination.total.toLocaleString()} suppliers indexed in the local investigation database.`}
      />
      <ListControls
        placeholder="Search company name or registration number…"
        total={data.pagination.total}
        limit={limit}
        offset={offset}
      />

      {data.items.length === 0 ? (
        <EmptyState
          icon={<Building2 className="h-5 w-5" />}
          title="No companies found"
          message={q ? `“${q}” is not available among imported companies.` : "No companies have been imported yet."}
          suggestions={q ? undefined : [
            "Run an investigation - entities are resolved and cataloged automatically",
            "Import tenders or awards - companies are extracted from procurement records",
            "Connect a procurement source in Settings -> Data Sources"
          ]}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((c) => (
            <div
              key={c.id}
              className="group relative overflow-hidden rounded-2xl border border-border bg-surface p-4 transition duration-300 hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-[0_20px_50px_-20px_rgba(0,0,0,0.8)]"
            >
              <div className="absolute -right-10 -top-10 h-24 w-24 rounded-full bg-accent/10 blur-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              <div className="relative flex items-start justify-between gap-3">
                <Link href={`/companies/${c.id}`} className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent" aria-label={`Open ${c.name}`}>
                  <Building2 className="h-5 w-5" />
                </Link>
                <ArrowUpRight className="h-4 w-4 text-faint transition group-hover:text-accent" aria-hidden="true" />
              </div>
              <Link href={`/companies/${c.id}`} className="relative mt-3 block truncate text-sm font-semibold text-text" title={c.name}>
                {c.name}
              </Link>
              <Link href={`/companies/${c.id}`} className="relative mt-1 block font-mono text-xs text-muted">
                {c.registration_number ?? "No registration number"}
              </Link>
              <div className="relative mt-4 flex items-center justify-between gap-3">
                <span className="text-[11px] text-faint">Indexed {formatDate(c.created_at)}</span>
                <InvestigateAction query={c.name} size="sm" label="Investigate" variant="subtle" />
              </div>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  );
}
