"use client";

import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page";
import { ErrorState } from "@/components/ui/states";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <PageShell>
      <ErrorState
        title="Unable to load company investigation"
        message="The backend API did not return the company investigation data."
      />
      <div className="mt-8 flex justify-center gap-3">
        <Button onClick={reset}>Retry</Button>
        <Button href="/" variant="subtle">
          Dashboard
        </Button>
      </div>
    </PageShell>
  );
}
