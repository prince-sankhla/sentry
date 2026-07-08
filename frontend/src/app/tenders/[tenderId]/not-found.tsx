import Link from "next/link";
import { FileSearch } from "lucide-react";

import { PageShell } from "@/components/ui/page";
import { EmptyState } from "@/components/ui/states";

export default function NotFound() {
  return (
    <PageShell>
      <EmptyState
        icon={<FileSearch className="h-5 w-5" />}
        title="Tender not found"
        message="This tender is not available in the backend database."
        action={
          <Link
            className="inline-flex rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text transition hover:border-border-strong"
            href="/tenders"
          >
            Back to tenders
          </Link>
        }
      />
    </PageShell>
  );
}
