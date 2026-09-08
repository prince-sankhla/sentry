import { InvestigationWebResearch } from "@/components/intel/investigation-web-research";
import { InvestigationPhases } from "@/components/intel/investigation-phases";
import { RealAuditCaseStudio } from "@/components/intel/real-audit-case-studio";
import { InvestigationWorkspace } from "../investigation-workspace";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    q?: string;
    case?: string;
  }>;
};

export default async function InvestigatePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const initialQuery = (params.q ?? "").trim();
  const auditCase = (params.case ?? "").trim();

  if (auditCase) {
    return (
      <>
        <InvestigationPhases active="intelligence" completed={[]} />
        <RealAuditCaseStudio caseKey={auditCase} />
      </>
    );
  }

  return (
    <>
      <InvestigationPhases active="intelligence" completed={[]} />
      {initialQuery ? <InvestigationWebResearch initialQuery={initialQuery} /> : null}
      <InvestigationWorkspace initialQuery={initialQuery} />
    </>
  );
}
