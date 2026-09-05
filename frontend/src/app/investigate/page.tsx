import { InvestigationPhases } from "@/components/intel/investigation-phases";
import { InvestigationWorkspace } from "../investigation-workspace";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    q?: string;
  }>;
};

export default async function InvestigatePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const initialQuery = (params.q ?? "").trim();

  return (
    <>
      <InvestigationPhases
        active={initialQuery ? "intelligence" : "intelligence"}
        completed={[]}
      />
      <InvestigationWorkspace initialQuery={initialQuery} />
    </>
  );
}
