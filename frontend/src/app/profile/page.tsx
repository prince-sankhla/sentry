import Link from "next/link";
import { Activity, FolderSearch, GitBranch, Mail, Radar, ShieldAlert, UserCircle } from "lucide-react";
import { getAnalyticsOverview, getRisk } from "@/lib/api";
import { PageHeader, PageShell, Badge, SeverityBadge } from "@/components/ui/page";
import { Section, StatCard, SurfaceCard } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  let overview;
  let risk;
  try {
    [overview, risk] = await Promise.all([getAnalyticsOverview(), getRisk()]);
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Account" title="Analyst Profile" />
        <ErrorState message="Could not load the analyst workspace snapshot." />
      </PageShell>
    );
  }

  const { totals } = overview;
  const topSignals = risk.signals.slice(0, 5);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Account"
        title="Analyst Profile"
        subtitle="Your SENTRY investigation workspace and current portfolio coverage."
      />

      <section className="grid w-full gap-5 xl:grid-cols-[360px_1fr]">
        <aside className="space-y-5">
          <SurfaceCard className="p-5">
            <div className="flex items-center gap-4">
              <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl border border-accent/30 bg-accent/10 text-accent glow-border">
                <UserCircle className="h-9 w-9" />
              </span>
              <div className="min-w-0">
                <div className="text-lg font-semibold text-text">Analyst</div>
                <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted">
                  <Mail className="h-3.5 w-3.5" /> analyst@sentry.local
                </div>
                <div className="mt-2">
                  <Badge tone="accent">Investigation access</Badge>
                </div>
              </div>
            </div>
          </SurfaceCard>

          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Tenders" value={formatNumber(totals.tenders)} tone="accent" />
            <StatCard label="Companies" value={formatNumber(totals.companies)} />
            <StatCard label="Awards" value={formatNumber(totals.awards)} tone="success" />
            <StatCard label="Risk signals" value={formatNumber(risk.summary.total)} tone="danger" icon={<Radar className="h-4 w-4" />} />
          </div>
        </aside>

        <div className="space-y-5">
          <Section eyebrow="Workspace" title="Quick actions">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Action href="/investigations" icon={<FolderSearch className="h-4 w-4" />} label="New investigation" hint="Launch a workflow" />
              <Action href="/graph" icon={<GitBranch className="h-4 w-4" />} label="Graph explorer" hint="Map relationships" />
              <Action href="/risk" icon={<ShieldAlert className="h-4 w-4" />} label="Risk monitor" hint={`${risk.summary.high} high signals`} />
            </div>
          </Section>

          <Section
            eyebrow="Attention"
            title="Top risk signals in your portfolio"
            action={<Link href="/risk" className="text-xs text-accent hover:underline">Monitor →</Link>}
          >
            {topSignals.length === 0 ? (
              <EmptyState icon={<Activity className="h-5 w-5" />} message="No risk signals in the current dataset." />
            ) : (
              <ul className="divide-y divide-border">
                {topSignals.map((s, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <div className="truncate text-sm text-text">{s.supplier_name ?? s.title}</div>
                      <div className="truncate text-xs text-faint">{s.buyer ?? s.summary}</div>
                    </div>
                    <SeverityBadge severity={s.severity} score={s.score} />
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      </section>
    </PageShell>
  );
}

function Action({
  href,
  icon,
  label,
  hint
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  hint: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-[14px] border border-border bg-surface p-4 transition hover:-translate-y-0.5 hover:border-accent/40"
    >
      <span className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-bg-2 text-accent transition group-hover:border-accent/40">
        {icon}
      </span>
      <div className="mt-3 text-sm font-medium text-text">{label}</div>
      <div className="mt-0.5 text-xs text-faint">{hint}</div>
    </Link>
  );
}
