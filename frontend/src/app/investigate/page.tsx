import { InvestigationWebResearch } from "@/components/intel/investigation-web-research";
import { InvestigationPhases } from "@/components/intel/investigation-phases";
import { PhysicalVerificationHandoff } from "@/components/intel/physical-verification-handoff";
import { PhysicalTenderRecommendationsLoader } from "@/components/intel/physical-tender-recommendations-loader";
import { RealAuditCaseLauncher } from "@/components/intel/real-audit-case-launcher";
import { InvestigationWorkspace } from "../investigation-workspace";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    q?: string;
    case?: string;
  }>;
};

const CASE_TO_QUERY: Record<string, string> = {
  "delhi-cwg": "CAG Performance Audit Report No. 4 of 2011 · Street Lighting",
  "dhanbad-led": "CAG Annual Technical Inspection Report on Local Bodies · 2017",
};

export default async function InvestigatePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const explicitQuery = (params.q ?? "").trim();
  const caseQuery = CASE_TO_QUERY[(params.case ?? "").trim()] ?? "";
  const initialQuery = explicitQuery || caseQuery;
  const landing = !initialQuery;

  return (
    <>
      <InvestigationPhases active="intelligence" completed={[]} />
      {landing ? <PhysicalTenderRecommendationsLoader /> : null}
      <RealAuditCaseLauncher />
      {initialQuery ? <InvestigationWebResearch initialQuery={initialQuery} /> : null}
      <InvestigationWorkspace initialQuery={initialQuery} />
      {initialQuery ? <PhysicalVerificationHandoff initialQuery={initialQuery} /> : null}
    </>
  );
}
