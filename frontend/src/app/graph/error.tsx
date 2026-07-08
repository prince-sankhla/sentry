"use client";

import Link from "next/link";

import { PageShell } from "@/components/ui/page";
import { ErrorState } from "@/components/ui/states";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <PageShell>
      <ErrorState
        title="Unable to load graph"
        message="The investigation graph API did not return a successful response."
      />
      <div className="mt-5 flex justify-center gap-3">
        <button
          className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text transition hover:border-border-strong"
          onClick={reset}
          type="button"
        >
          Retry
        </button>
        <Link
          className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text transition hover:border-border-strong"
          href="/"
        >
          Dashboard
        </Link>
      </div>
    </PageShell>
  );
}
