import Link from "next/link";
import { ArrowRight, ClipboardCheck, FileCheck2, FolderSearch, GitBranch, Radar, Search, ShieldCheck } from "lucide-react";
import { PageHeader, PageShell } from "@/components/ui/page";

const demoSteps = [
  { href: "/investigate?q=Dharmagarh%20NAC", icon: FolderSearch, label: "1 · Start investigation", detail: "Open a concrete procurement subject and run the investigation-first workflow." },
  { href: "/verification?q=Dharmagarh%20NAC", icon: FileCheck2, label: "2 · Verify evidence", detail: "Show how evidence quality, provenance and reasoning stay separate." },
  { href: "/graph", icon: GitBranch, label: "3 · Connect the ecosystem", detail: "Move from isolated records to buyer, tender, award and supplier relationships." },
  { href: "/review?q=Dharmagarh%20NAC", icon: ClipboardCheck, label: "4 · Prepare review", detail: "Turn the investigation into a traceable human-review handoff." },
  { href: "/review/inbox", icon: Search, label: "5 · Government intake", detail: "Open the review inbox and show the human-review boundary." },
  { href: "/cases", icon: ShieldCheck, label: "6 · Manage the case", detail: "Walk through government case lifecycle and reviewer workflow." }
];

export default function DemoPage() {
  return (
    <PageShell>
      <PageHeader
        eyebrow="Hackathon / Demo Runbook"
        title="SENTRY in six deliberate steps"
        subtitle="A judge-friendly path through the product: detect → explain → connect → verify → review → manage. Each surface keeps evidence, uncertainty and human decision-making explicit."
        actions={<Link href="/investigate?q=Dharmagarh%20NAC" className="inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-bg transition hover:brightness-110"><Radar className="h-4 w-4" />Start demo</Link>}
      />

      <div className="rounded-3xl border border-accent/20 bg-accent/[0.045] p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-accent/25 bg-accent/10 text-accent"><ShieldCheck className="h-5 w-5" /></span>
          <div>
            <div className="text-sm font-semibold text-text">The product story is the evidence chain.</div>
            <p className="mt-1 text-xs leading-5 text-muted">SENTRY surfaces review leads from official procurement records, preserves provenance, exposes evidence gaps and alternative explanations, and leaves the final decision with a human reviewer.</p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {demoSteps.map((step) => {
          const Icon = step.icon;
          return (
            <Link key={step.href} href={step.href} className="group rounded-2xl border border-border bg-surface/70 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-2">
              <div className="flex items-center justify-between">
                <span className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-bg-2 text-accent"><Icon className="h-4 w-4" /></span>
                <ArrowRight className="h-4 w-4 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent" />
              </div>
              <div className="mt-4 text-sm font-semibold text-text">{step.label}</div>
              <p className="mt-1.5 text-xs leading-5 text-muted">{step.detail}</p>
            </Link>
          );
        })}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <Proof label="Deterministic risk" value="Rules + explainability" />
        <Proof label="Evidence standard" value="Provenance + gaps" />
        <Proof label="Decision boundary" value="Human review" />
      </div>

      <p className="mt-6 text-[11px] leading-relaxed text-faint">Demo routes use the existing SENTRY investigation surfaces. Government review and case-management state are intentionally presented as human-workflow prototypes unless backed by a shared server-side system of record.</p>
    </PageShell>
  );
}

function Proof({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-border bg-bg-2/55 p-4"><div className="t-label">{label}</div><div className="mt-1 text-sm font-semibold text-text">{value}</div></div>;
}
