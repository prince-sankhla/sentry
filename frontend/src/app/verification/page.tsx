import { EvidenceVerification } from "@/components/intel/evidence-verification";
import { PageShell } from "@/components/ui/page";

type PageProps = {
  searchParams: Promise<{ q?: string }>;
};

export const dynamic = "force-dynamic";

export default async function VerificationPage({ searchParams }: PageProps) {
  const params = await searchParams;

  return (
    <PageShell>
      <EvidenceVerification data={null} initialQuery={(params.q ?? "").trim()} />
    </PageShell>
  );
}
