import { Database, Server, SlidersHorizontal, Shield } from "lucide-react";
import { getAnalyticsOverview } from "@/lib/api";
import { PageHeader, PageShell, RankBar, Badge } from "@/components/ui/page";
import { Section, StatCard } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatNumber } from "@/lib/format";
import { SettingsPreferences } from "./settings-preferences";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

export default async function SettingsPage() {
  let overview;
  try {
    overview = await getAnalyticsOverview();
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="System" title="Settings" />
        <ErrorState message="Could not reach the backend to load platform status." />
      </PageShell>
    );
  }

  const { totals, sources } = overview;
  const maxSource = Math.max(1, ...sources.map((s) => s.tenders));

  return (
    <PageShell>
      <PageHeader
        eyebrow="System"
        title="Settings"
        subtitle="Data sources, platform status, and analyst workspace preferences."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Connected sources" value={String(sources.length)} tone="accent" icon={<Database className="h-4 w-4" />} />
        <StatCard label="Indexed tenders" value={formatNumber(totals.tenders)} icon={<Server className="h-4 w-4" />} />
        <StatCard label="Companies" value={formatNumber(totals.companies)} />
        <StatCard label="Awards" value={formatNumber(totals.awards)} tone="success" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Section eyebrow="Ingestion" title="Connected data sources">
          {sources.length === 0 ? (
            <EmptyState icon={<Database className="h-5 w-5" />} title="No sources connected" message="Run the import engine to ingest procurement records." />
          ) : (
            <div className="space-y-3.5">
              {sources.map((s) => (
                <RankBar
                  key={s.source_name}
                  label={s.source_name}
                  value={s.tenders}
                  max={maxSource}
                  meta={`${formatNumber(s.tenders)} tenders`}
                  tone="info"
                />
              ))}
            </div>
          )}
        </Section>

        <Section
          eyebrow="Workspace"
          title="Investigation preferences"
          action={<SlidersHorizontal className="h-4 w-4 text-faint" />}
        >
          <SettingsPreferences />
        </Section>

        <Section eyebrow="Platform" title="System status">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Field label="API endpoint" value={BACKEND_URL} mono />
            <Field label="Environment" value="Production data" />
            <Field label="Total tender value" value={`${formatNumber(Number(totals.total_tender_value))}`} mono />
            <Field label="Single-bidder flags" value={formatNumber(totals.single_bidder_tenders)} />
          </dl>
          <div className="mt-4 flex items-center gap-2">
            <Badge tone="success">
              <span className="h-1.5 w-1.5 rounded-full bg-current" /> Backend online
            </Badge>
            <Badge tone="accent">PostgreSQL</Badge>
            <Badge tone="info">FastAPI</Badge>
          </div>
        </Section>

        <Section eyebrow="Access" title="Role & permissions">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-accent/30 bg-accent/10 text-accent">
              <Shield className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-text">Analyst</div>
              <p className="mt-1 text-xs text-muted">
                Full read access to imported procurement records, investigations, graph, and
                risk analytics. Import and administrative controls are managed server-side.
              </p>
            </div>
          </div>
        </Section>
      </div>
    </PageShell>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-bg-2/40 p-3">
      <div className="text-[11px] text-faint">{label}</div>
      <div className={`mt-1 truncate text-sm text-text ${mono ? "font-mono text-xs" : ""}`} title={value}>
        {value}
      </div>
    </div>
  );
}
