import { PageShell } from "@/components/ui/page";
import { FieldMissionConsoleV2 } from "@/components/field/field_mission_console_v2";
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
        <FieldMissionConsoleV2
          tenderKey={tenderKey || undefined}
          requirementId={requirementId || undefined}
        />
        <FieldEvidenceMap tenderKey={tenderKey || undefined} />
      </div>
    </PageShell>
  );
}
