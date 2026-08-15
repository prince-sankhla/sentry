"use client";

import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/page";
import { ErrorState } from "@/components/ui/states";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <PageShell>
      <ErrorState
        title="Something went wrong"
        message="The backend API did not return a successful response."
      />
      <div className="mt-8 flex justify-center">
        <Button onClick={reset}>Retry</Button>
      </div>
    </PageShell>
  );
}
