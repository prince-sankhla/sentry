import { PageShell } from "@/components/ui/page";
import { FieldMissionConsole } from "@/components/field/field-mission-console";
import { FieldEvidenceMap } from "@/components/field/field_evidence_map";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    tender?: string;
    requirement?: string;
  }>;
};

export default async function FieldPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const tenderKey = (params.tender ?? "").trim();
  const requirementId = (params.requirement ?? "").trim();

  return (
    <PageShell>
      <div className="space-y-5">
        <FieldMissionConsole tenderKey={tenderKey || undefined} requirementId={requirementId || undefined} />
        <FieldEvidenceMap />
      </div>
    </PageShell>
  );
}
