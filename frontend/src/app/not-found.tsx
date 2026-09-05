import Link from "next/link";
import { ArrowLeft, SearchX } from "lucide-react";
import { PageShell } from "@/components/ui/page";

export default function NotFound() {
  return (
    <PageShell>
      <div className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center text-center">
        <span className="grid h-12 w-12 place-items-center rounded-2xl border border-border bg-surface text-faint">
          <SearchX className="h-5 w-5" />
        </span>
        <div className="mt-5 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">404 · Route not found</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-text">That workspace surface is not available.</h1>
        <p className="mt-2 text-sm leading-6 text-muted">The route may have moved, or the requested resource may no longer exist. Continue from the investigation workspace.</p>
        <Link href="/investigations" className="mt-6 inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-bg transition hover:brightness-110">
          <ArrowLeft className="h-4 w-4" />
          Back to investigations
        </Link>
      </div>
    </PageShell>
  );
}
