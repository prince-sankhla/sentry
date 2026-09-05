import { GuidedResearch } from "@/components/intel/guided-research";
import { PageShell } from "@/components/ui/page";

type PageProps = {
  searchParams: Promise<{ q?: string }>;
};

export const dynamic = "force-dynamic";

export default async function ResearchPage({ searchParams }: PageProps) {
  const params = await searchParams;

  return (
    <PageShell>
      <GuidedResearch initialQuery={(params.q ?? "").trim()} />
    </PageShell>
  );
}
