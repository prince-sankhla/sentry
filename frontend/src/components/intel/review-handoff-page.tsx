"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ClipboardList, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { ReviewHandoff } from "@/components/intel/review-handoff";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Button } from "@/components/ui/button";
import { streamInvestigation, type InvestigationPackage, type InvestigationReasoning, type InvestigationStreamStep } from "@/lib/api";

export function ReviewHandoffPage({ initialQuery }: { initialQuery: string }) {
  const router = useRouter();
  const [pkg, setPkg] = useState<InvestigationPackage | null>(null);
  const [reasoning, setReasoning] = useState<InvestigationReasoning | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("Preparing evidence review…");

  const run = useCallback((query: string) => {
    setRunning(true);
    setError(null);
    setPkg(null);
    setReasoning(null);
    setStatus("Assembling the verified investigation package…");

    const stop = streamInvestigation(query, {
      onStep: (step: InvestigationStreamStep) => setStatus(step.detail ?? step.label),
      onReport: (report) => {
        setPkg(report.package);
        setReasoning(report.reasoning);
        setStatus("Evidence package ready for human review.");
        setRunning(false);
      },
      onError: (message) => {
        setError(message);
        setRunning(false);
      }
    });

    return stop;
  }, []);

  useEffect(() => {
    if (!initialQuery) return;
    return run(initialQuery);
  }, [initialQuery, run]);

  if (!initialQuery) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-5 w-5" />}
        title="No investigation selected"
        message="Open a completed investigation first, then prepare its evidence for official human review."
        action={<Button onClick={() => router.push("/investigations")}>Open investigation workspace</Button>}
      />
    );
  }

  if (error) {
    return <ErrorState title="Review package could not be prepared" message={error} />;
  }

  if (running || !pkg || !reasoning) {
    return (
      <div className="rounded-2xl border border-border bg-surface/70 p-6">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-accent/25 bg-accent/10 text-accent">
            <Loader2 className="h-4 w-4 animate-spin" />
          </span>
          <div>
            <div className="text-sm font-semibold text-text">Preparing review handoff</div>
            <div className="mt-1 text-xs text-muted">{status}</div>
          </div>
        </div>
        <div className="mt-5 rounded-xl border border-warning/20 bg-warning/[0.04] p-3 text-[11px] leading-relaxed text-muted">
          <AlertTriangle className="mr-1 inline h-3.5 w-3.5 text-warning" />
          Review handoff is a human-review workflow. It does not adjudicate wrongdoing and does not submit to a government system automatically.
        </div>
      </div>
    );
  }

  return <ReviewHandoff pkg={pkg} reasoning={reasoning} />;
}
