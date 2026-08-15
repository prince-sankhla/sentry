"use client";

import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page";
import { ErrorState } from "@/components/ui/states";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <PageShell>
      <ErrorState
        title="Unable to load tender"
        message="The tender details could not be loaded from the backend API."
      />
      <div className="mt-8 flex justify-center gap-3">
        <Button onClick={reset}>Retry</Button>
        <Button href="/tenders" variant="subtle">
          Tenders
        </Button>
      </div>
    </PageShell>
  );
}
