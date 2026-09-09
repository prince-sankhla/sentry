import { PageShell } from "@/components/ui/page";
import { FieldHandoffConsole } from "@/components/field/field-handoff-console";
import { MobileGpsSession } from "@/components/field/mobile-gps-session";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    tender?: string;
    requirement?: string;
  }>;
};

export default async function FieldPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const tenderKey = (params.tender ?? "").trim();
  const requirementId = (params.requirement ?? "").trim();

  return (
    <PageShell>
      {tenderKey && requirementId ? (
        <div className="space-y-5">
          <FieldHandoffConsole tenderKey={tenderKey} requirementId={requirementId} />
          <MobileGpsSession tenderKey={tenderKey} requirementId={requirementId} />
        </div>
      ) : (
        <section className="rounded-2xl border border-border bg-surface p-8 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">SENTRY FIELD</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">No mission context supplied</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">Open SENTRY FIELD from an authorised investigation handoff so the exact tender and inspection requirement remain linked to the mission.</p>
        </section>
      )}
    </PageShell>
  );
}
