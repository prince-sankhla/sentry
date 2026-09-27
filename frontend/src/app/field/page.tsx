import { PageHeader, PageShell } from "@/components/ui/page";
import { FieldMissionConsoleLive } from "@/components/field/field_mission_console_live";
import { FieldEvidenceMap } from "@/components/field/field_evidence_map";
import { HistoricalFieldEvidence } from "@/components/field/historical_field_evidence";
import { FieldTenderQueue } from "@/components/field/field-tender-queue";
import { FieldVerificationCloseout } from "@/components/intel/field-verification-closeout";

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
      <div className="space-y-6">
        {!tenderKey ? (
          <>
            <PageHeader
              eyebrow="Physical Verification"
              title="FIELD Verification Queue"
              subtitle="Physical-verification tenders stay in their own workspace. Select a tender to launch the mission and return evidence to SENTRY."
            />
            <FieldTenderQueue />
          </>
        ) : (
          <>
            <FieldMissionConsoleLive
              tenderKey={tenderKey}
              requirementId={requirementId || undefined}
            />
            <FieldEvidenceMap tenderKey={tenderKey} />
            <HistoricalFieldEvidence tenderKey={tenderKey} />
            <FieldVerificationCloseout tenderKey={tenderKey} />
          </>
        )}
      </div>
    </PageShell>
  );
}
