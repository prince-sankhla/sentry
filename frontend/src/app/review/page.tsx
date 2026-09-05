import { ReviewHandoffPage } from "@/components/intel/review-handoff-page";
import { PageHeader, PageShell } from "@/components/ui/page";

type PageProps = {
  searchParams: Promise<{ q?: string }>;
};

export const dynamic = "force-dynamic";

export default async function ReviewPage({ searchParams }: PageProps) {
  const params = await searchParams;

  return (
    <PageShell>
      <PageHeader
        eyebrow="Review workflow"
        title="Prepare official review"
        subtitle="Package a completed investigation as a traceable human-review handoff. Nothing is adjudicated or submitted automatically."
      />
      <ReviewHandoffPage initialQuery={(params.q ?? "").trim()} />
    </PageShell>
  );
}
