import { AlertTriangle, Radar, ShieldAlert, TrendingUp, Users } from "lucide-react";
import Link from "next/link";
import { getRisk, type RiskSignal } from "@/lib/api";
import { PageHeader, PageShell, SeverityBadge } from "@/components/ui/page";
import { StatCard } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";

export const dynamic = "force-dynamic";

function tenderHref(sig: RiskSignal): string | null {
  return sig.tender_id ? `/tenders/${sig.tender_id}` : null;
}
function supplierHref(sig: RiskSignal): string | null {
  return sig.supplier_id ? `/companies/${sig.supplier_id}` : null;
}

export default async function RiskPage() {
  let data;
  try {
    data = await getRisk();
  } catch {
    return (
      <PageShell>
        <PageHeader eyebrow="Intelligence" title="Risk Monitor" />
        <ErrorState message="Could not compute portfolio risk signals." />
      </PageShell>
    );
  }

  const { summary, signals } = data;

  return (
    <PageShell>
      <PageHeader
        eyebrow="Intelligence"
        title="Risk Monitor"
        subtitle="Red-flag indicators computed live across every imported tender, award, and buyer-supplier relationship."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard label="Total signals" value={String(summary.total)} tone="accent" icon={<Radar className="h-4 w-4" />} />
        <StatCard label="High severity" value={String(summary.high)} tone="danger" icon={<ShieldAlert className="h-4 w-4" />} />
        <StatCard label="Medium" value={String(summary.medium)} tone="warning" />
        <StatCard label="Single-bidder tenders" value={String(summary.single_bidder_tenders)} icon={<AlertTriangle className="h-4 w-4" />} />
        <StatCard label="Flagged relationships" value={String(summary.flagged_relationships)} icon={<Users className="h-4 w-4" />} />
      </div>

      {signals.length === 0 ? (
        <EmptyState
          icon={<Radar className="h-5 w-5" />}
          title="No risk signals detected"
          message="No single-bidder tenders or supplier concentration patterns were found in the current dataset."
        />
      ) : (
        <div className="space-y-3">
          {signals.map((sig, i) => {
            const th = tenderHref(sig);
            const sh = supplierHref(sig);
            return (
              <div
                key={`${sig.type}-${sig.tender_id ?? sig.supplier_id ?? i}`}
                className="animate-rise rounded-[16px] border border-border bg-surface p-5 transition hover:border-border-strong"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg border ${
                        sig.severity === "high"
                          ? "border-danger/40 bg-danger/10 text-danger"
                          : sig.severity === "medium"
                            ? "border-warning/40 bg-warning/10 text-warning"
                            : "border-success/40 bg-success/10 text-success"
                      }`}
                    >
                      <TrendingUp className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate text-sm font-semibold text-text">{sig.title}</h3>
                      </div>
                      <p className="mt-0.5 text-sm text-muted">{sig.summary}</p>
                    </div>
                  </div>
                  <SeverityBadge severity={sig.severity} score={sig.score} />
                </div>

                {sig.evidence.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 pl-12">
                    {sig.evidence.map((e, j) => (
                      <span
                        key={j}
                        className="rounded-md border border-border bg-bg-2 px-2 py-1 text-[11px] text-muted"
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-4 pl-12 text-xs">
                  {sig.buyer && <span className="text-faint">Buyer: <span className="text-muted">{sig.buyer}</span></span>}
                  {sh && (
                    <Link href={sh} className="text-accent hover:underline">
                      {sig.supplier_name ?? "View supplier"} →
                    </Link>
                  )}
                  {th && (
                    <Link href={th} className="text-accent hover:underline">
                      {sig.tender_reference ?? "View tender"} →
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </PageShell>
  );
}
