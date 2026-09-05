import { GovernmentCaseManagement } from "@/components/government/case-management";
import { PageHeader, PageShell } from "@/components/ui/page";

export const dynamic = "force-dynamic";

export default function CasesPage() {
  return (
    <PageShell>
      <PageHeader
        eyebrow="Government / Audit"
        title="Case management"
        subtitle="Prioritize, review, monitor, escalate, and close procurement cases with explicit human decision states."
      />
      <GovernmentCaseManagement />
    </PageShell>
  );
}
