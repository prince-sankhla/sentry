"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page";
import { ErrorState } from "@/components/ui/states";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <PageShell>
      <ErrorState
        title="This workspace surface hit an unexpected error"
        message="SENTRY could not complete this view. Your source records and risk calculations are unchanged; retry the surface before continuing the investigation."
      />
      <div className="mt-6 flex justify-center">
        <Button onClick={reset} icon={<RotateCcw className="h-4 w-4" />}>
          Retry workspace
        </Button>
      </div>
      <div className="mx-auto mt-4 max-w-lg rounded-xl border border-warning/20 bg-warning/[0.04] p-3 text-center text-[11px] leading-relaxed text-muted">
        <AlertTriangle className="mr-1 inline h-3.5 w-3.5 text-warning" />
        A UI error is not an evidence finding and does not alter investigation state.
      </div>
    </PageShell>
  );
}
