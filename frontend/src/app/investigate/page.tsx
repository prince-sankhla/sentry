import { InvestigationWebResearch } from "@/components/intel/investigation-web-research";
import { InvestigationPhases } from "@/components/intel/investigation-phases";
import { InvestigationWorkspace } from "../investigation-workspace";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{ q?: string; case?: string }>;
};

const CASE_TO_QUERY: Record<string, string> = {
  "delhi-cwg": "TENDER:AUDIT:2026_CAG_DELHI_CWG_STREETLIGHT",
  "dhanbad-led": "TENDER:AUDIT:2026_CAG_DHANBAD_LED",
};

export default async function InvestigatePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const explicitQuery = (params.q ?? "").trim();
  const caseQuery = CASE_TO_QUERY[(params.case ?? "").trim()] ?? "";
  const initialQuery = explicitQuery || caseQuery;

  return (
    <>
      <InvestigationPhases active="intelligence" completed={[]} />
      {initialQuery ? <InvestigationWebResearch initialQuery={initialQuery} /> : null}
      <InvestigationWorkspace initialQuery={initialQuery} />
    </>
  );
}
