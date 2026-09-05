import { OpenSourceContext } from "@/components/intel/open-source-context";
import { PageHeader, PageShell } from "@/components/ui/page";

type PageProps = { searchParams: Promise<{ q?: string }> };

export const dynamic = "force-dynamic";

export default async function ContextPage({ searchParams }: PageProps) {
  const params = await searchParams;
  return (
    <PageShell>
      <PageHeader
        eyebrow="Research context"
        title="Open-source procurement context"
        subtitle="Inspect current and historical web reporting, contract references and surrounding context without promoting it into official evidence or risk scoring."
      />
      <OpenSourceContext initialQuery={(params.q ?? "").trim()} />
    </PageShell>
  );
}
