import { InvestigationWebResearch } from "@/components/intel/investigation-web-research";
import { InvestigationPhases } from "@/components/intel/investigation-phases";
import { PhysicalVerificationHandoff } from "@/components/intel/physical-verification-handoff";
import { PhysicalTenderRecommendationsLoader } from "@/components/intel/physical-tender-recommendations-loader";
import { RealAuditCaseLauncher } from "@/components/intel/real-audit-case-launcher";
import { InvestigationWorkspace } from "../investigation-workspace";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{ q?: string; case?: string }>;
};

// Demo cases use exact tender references so they cannot drift into a generic
// company/buyer investigation because of wording in an audit title.
// InvestigationPlanner unwraps TENDER:<reference> and runs the precise tender flow.
const CASE_TO_QUERY: Record<string, string> = {
  "delhi-cwg": "TENDER:AUDIT:2026_CAG_DELHI_CWG_STREETLIGHT",
  "dhanbad-led": "TENDER:AUDIT:2026_CAG_DHANBAD_LED",
};

export default async function InvestigatePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const explicitQuery = (params.q ?? "").trim();
  const caseQuery = CASE_TO_QUERY[(params.case ?? "").trim()] ?? "";
  const initialQuery = explicitQuery || caseQuery;
  const landing = !initialQuery;
  const physicalReference = initialQuery.replace(/^TENDER:/i, "").trim();

  return (
    <>
      <InvestigationPhases active="intelligence" completed={[]} />
      {landing ? <PhysicalTenderRecommendationsLoader /> : null}
      <RealAuditCaseLauncher />
      {initialQuery ? <InvestigationWebResearch initialQuery={initialQuery} /> : null}
      <InvestigationWorkspace initialQuery={initialQuery} />
      {initialQuery ? <PhysicalVerificationHandoff initialQuery={physicalReference} /> : null}
    </>
  );
}
