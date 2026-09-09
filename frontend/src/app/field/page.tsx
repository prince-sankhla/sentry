import { PageShell } from "@/components/ui/page";
import { FieldMissionConsole } from "@/components/field/field_mission_console";
import { AutoFieldMissionConsole } from "@/components/field/auto_field_mission_console";
import { FieldEvidenceMap } from "@/components/field/field_evidence_map";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    tender?: string;
    requirement?: string;
  }>;
};

const UUID_TENDER = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default async function FieldPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const tenderKey = (params.tender ?? "").trim();
  const requirementId = (params.requirement ?? "").trim();
  const autoPlannedTender = UUID_TENDER.test(tenderKey);

  return (
    <PageShell>
      <div className="space-y-5">
        {autoPlannedTender ? (
          <AutoFieldMissionConsole tenderId={tenderKey} />
        ) : (
          <FieldMissionConsole tenderKey={tenderKey || undefined} requirementId={requirementId || undefined} />
        )}
        <FieldEvidenceMap />
      </div>
    </PageShell>
  );
}
