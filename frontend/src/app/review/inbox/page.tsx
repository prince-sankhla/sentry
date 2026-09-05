import { ReviewInbox } from "@/components/intel/review-inbox";
import { PageHeader, PageShell } from "@/components/ui/page";

export default function ReviewInboxPage() {
  return (
    <PageShell>
      <PageHeader
        eyebrow="Government / Audit"
        title="Official review inbox"
        subtitle="Review evidence-backed handoffs prepared by investigators and researchers. Intake is for human assessment, not automated adjudication."
      />
      <ReviewInbox />
    </PageShell>
  );
}
