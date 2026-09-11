import { PageShell } from "@/components/ui/page";
import { FieldMissionConsoleLive } from "@/components/field/field_mission_console_live";
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
        <FieldMissionConsoleLive
          tenderKey={tenderKey || undefined}
          requirementId={requirementId || undefined}
        />
        <FieldEvidenceMap tenderKey={tenderKey || undefined} />
      </div>
    </PageShell>
  );
}
