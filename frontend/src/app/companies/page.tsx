import Link from "next/link";
import { Building2, ArrowUpRight } from "lucide-react";
import { getCompanies } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { ListControls } from "@/components/ui/list-controls";
import { EmptyState, ErrorState } from "@/components/ui/states";
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
          message={
            q
              ? `“${q}” is not available among imported companies.`
              : "No companies have been imported yet."
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((c) => (
            <Link
              key={c.id}
              href={`/companies/${c.id}`}
              className="group relative overflow-hidden rounded-[16px] border border-border bg-surface p-4 transition hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-[0_20px_50px_-20px_rgba(0,0,0,0.8)]"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent">
                  <Building2 className="h-5 w-5" />
                </span>
                <ArrowUpRight className="h-4 w-4 text-faint transition group-hover:text-accent" />
              </div>
              <div className="mt-3 truncate text-sm font-semibold text-text" title={c.name}>
                {c.name}
              </div>
              <div className="mt-1 font-mono text-xs text-muted">
                {c.registration_number ?? "No registration number"}
              </div>
              <div className="mt-3 text-[11px] text-faint">
                Indexed {formatDate(c.created_at)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </PageShell>
  );
}
