import { Award, BarChart3, Building2, CheckCircle2, FileCheck2, FileText, GitBranch, Map, Radar, Search, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { getDashboardRecent, getDashboardSummary, getRisk } from "@/lib/api";
import { PageHeader, PageShell } from "@/components/ui/page";
import { Section, StatCard } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { InvestigateAction } from "@/components/intel/investigate-action";
import { formatDate, formatMoneyFull } from "@/lib/format";
import { InvestigationLauncher } from "./investigation-launcher";
import { LiveTenderIngestion } from "./live-tender-ingestion";

export const dynamic = "force-dynamic";

const intelligenceSurfaces = [
  { href: "/tenders", icon: FileText, label: "Tender Intelligence", detail: "Lifecycle, buyer, awards, documents and benchmark context." },
  { href: "/companies", icon: Building2, label: "Supplier Intelligence", detail: "Award history, concentration, buyer relationships and repeat-winner context." },
  { href: "/buyers", icon: Search, label: "Buyer Intelligence", detail: "Procurement behaviour, supplier distribution, timing and source-backed observations." },
  { href: "/risk", icon: Radar, label: "Risk Assessment", detail: "Deterministic screening signals with evidence-aware review priorities." },
  { href: "/graph", icon: GitBranch, label: "Relationship Graph", detail: "Connect buyers, tenders, suppliers, awards, documents and evidence." },
  { href: "/timeline", icon: BarChart3, label: "Timeline Analysis", detail: "Follow procurement events as an investigation sequence." },
  { href: "/map", icon: Map, label: "Geography", detail: "Explore procurement activity spatially across the Indian dataset." },
  { href: "/reports", icon: FileCheck2, label: "Reports & Evidence", detail: "Move from review signals to grounded analyst output." }
];

const investigationStages = [
  { num: "01", title: "Intelligence", detail: "Start from a verified entity and assemble what SENTRY already knows." },
  { num: "02", title: "Evidence gaps", detail: "Identify the missing records, documents or context that matter most." },
  { num: "03", title: "Corroboration", detail: "Cross-check source material, relationships and newly supplied evidence." },
  { num: "04", title: "Assessment", detail: "Produce an evidence-backed review with limitations and next actions." }
];

export default async function InvestigationsPage() {
  const [recent, summary, risk] = await Promise.all([
    getDashboardRecent(6).catch(() => ({ latest_tenders: [], latest_awarded_companies: [], latest_awards: [] })),
    getDashboardSummary().catch(() => null),
    getRisk().catch(() => null)
  ]);

  const suggestions = Array.from(
    new Set([
      ...recent.latest_tenders.map((t) => t.procuring_entity),
      ...recent.latest_awarded_companies.map((c) => c.name)
    ].filter((s): s is string => Boolean(s)))
  ).slice(0, 4);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Investigation Workspace"
        title="Start with a question. Follow the evidence."
        subtitle="Use SENTRY to move from a verified procurement entity to an evidence-backed investigation without losing source provenance or analytical context."
        actions={
          <Link href="/investigate" className="inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-bg transition hover:brightness-110">
            <Sparkles className="h-4 w-4" />
            Start investigation
          </Link>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard label="Tenders indexed" value={summary ? String(summary.total_tenders) : "—"} tone="accent" icon={<FileText className="h-4 w-4" />} />
        <StatCard label="Suppliers" value={summary ? String(summary.total_companies) : "—"} icon={<Building2 className="h-4 w-4" />} />
        <StatCard label="Awards" value={summary ? String(summary.total_awards) : "—"} icon={<Award className="h-4 w-4" />} />
        <StatCard label="Review signals" value={risk ? String(risk.summary.total) : "—"} tone={risk?.summary.high ? "danger" : "accent"} icon={<Radar className="h-4 w-4" />} />
        <StatCard label="System status" value="Operational" icon={<CheckCircle2 className="h-4 w-4" />} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.55fr_.45fr]">
        <section className="overflow-hidden rounded-3xl border border-border bg-surface elevate">
          <div className="border-b border-border bg-bg-2/60 px-6 py-5 sm:px-7">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
              <Sparkles className="h-3.5 w-3.5" /> Investigation flow
            </div>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-text">A four-stage investigation, with evidence at every step.</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
              SENTRY starts with grounded procurement intelligence, identifies the strongest evidence gaps, then carries the investigation through corroboration and final assessment.
            </p>
          </div>
          <div className="grid gap-px bg-border md:grid-cols-2 xl:grid-cols-4">
            {investigationStages.map((stage, index) => (
              <div key={stage.num} className="group bg-surface p-5 transition hover:bg-surface-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] tracking-[0.14em] text-faint">{stage.num}</span>
                  {index < investigationStages.length - 1 ? <span className="hidden text-border-strong xl:block">→</span> : null}
                </div>
                <div className="mt-5 text-sm font-semibold text-text">{stage.title}</div>
                <p className="mt-1.5 text-xs leading-5 text-muted">{stage.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-accent/20 bg-accent/[0.05] p-6 elevate">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-accent/25 bg-accent/10 text-accent">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-accent">Evidence standard</div>
          <h2 className="mt-2 text-lg font-semibold text-text">Facts first. Review leads, not verdicts.</h2>
          <p className="mt-2 text-sm leading-6 text-muted">Each surfaced observation keeps its source, evidence coverage, missing information and alternative explanations visible.</p>
          <div className="mt-5 grid grid-cols-2 gap-2 text-xs">
            <Signal label="Source provenance" value="Visible" />
            <Signal label="Missing data" value="Neutral" />
            <Signal label="AI grounding" value="Tracked" />
            <Signal label="Decision" value="Human-led" />
          </div>
        </section>
      </div>

      <Section eyebrow="Investigation surfaces" title="Choose the intelligence layer you need" className="mt-7">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {intelligenceSurfaces.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className="group rounded-2xl border border-border bg-bg-2 p-4 transition duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-2">
                <div className="flex items-center justify-between">
                  <span className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-accent"><Icon className="h-4 w-4" /></span>
                  <span className="text-xs text-faint transition group-hover:text-accent">Open →</span>
                </div>
                <div className="mt-4 text-sm font-semibold text-text">{item.label}</div>
                <p className="mt-1 text-xs leading-5 text-muted">{item.detail}</p>
              </Link>
            );
          })}
        </div>
      </Section>

      <LiveTenderIngestion />
      <div className="mt-6"><InvestigationLauncher suggestions={suggestions} /></div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Section eyebrow="Latest" title="Tender records" action={<Link href="/tenders" className="text-xs text-accent hover:underline">View all →</Link>}>
          {recent.latest_tenders.length === 0 ? <EmptyState message="No tenders imported yet." /> : <ul className="space-y-2">{recent.latest_tenders.map((t) => <li key={t.id} className="flex items-center gap-2 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2"><Link href={`/tenders/${t.id}`} className="flex min-w-0 flex-1 items-start gap-3"><FileText className="mt-0.5 h-4 w-4 shrink-0 text-info" /><span className="min-w-0"><span className="block truncate text-sm text-text">{t.title}</span><span className="block truncate text-xs text-faint">{t.procuring_entity ?? "Procuring entity not available"} · {formatMoneyFull(t.estimated_value, t.currency)}</span></span></Link><InvestigateAction query={t.reference_number} size="sm" label="Investigate" variant="subtle" /></li>)}</ul>}
        </Section>

        <Section eyebrow="Latest" title="Supplier records" action={<Link href="/companies" className="text-xs text-accent hover:underline">View all →</Link>}>
          {recent.latest_awarded_companies.length === 0 ? <EmptyState message="No supplier records imported yet." /> : <ul className="space-y-2">{recent.latest_awarded_companies.map((c) => <li key={c.id} className="flex items-center gap-2 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2"><Link href={`/companies/${c.id}`} className="flex min-w-0 flex-1 items-start gap-3"><Building2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" /><span className="min-w-0"><span className="block truncate text-sm text-text">{c.name}</span><span className="block truncate font-mono text-xs text-faint">{c.registration_number ?? "Registration not available"}</span></span></Link><InvestigateAction query={c.name} size="sm" label="Investigate" variant="subtle" /></li>)}</ul>}
        </Section>

        <Section eyebrow="Latest" title="Award records" action={<Link href="/awards" className="text-xs text-accent hover:underline">View all →</Link>}>
          {recent.latest_awards.length === 0 ? <EmptyState message="No award records imported yet." /> : <ul className="space-y-2">{recent.latest_awards.map((a) => <li key={a.id} className="flex items-center gap-2 rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surface-2"><Link href={`/companies/${a.company.id}`} className="flex min-w-0 flex-1 items-start gap-3"><Award className="mt-0.5 h-4 w-4 shrink-0 text-success" /><span className="min-w-0"><span className="block truncate text-sm text-text">{a.company.name}</span><span className="block truncate text-xs text-faint">{formatMoneyFull(a.award_value, a.currency)} · {formatDate(a.award_date)}</span></span></Link><InvestigateAction query={a.company.name} size="sm" label="Investigate" variant="subtle" /></li>)}</ul>}
        </Section>
      </div>
    </PageShell>
  );
}

function Signal({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface/70 px-3 py-2.5">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-1 text-sm font-semibold text-text">{value}</div>
    </div>
  );
}
