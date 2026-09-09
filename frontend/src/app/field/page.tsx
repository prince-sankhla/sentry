import { PageShell } from "@/components/ui/page";
import { FieldEvidenceMap } from "@/components/field/field_evidence_map";
import { FieldHandoffConsole } from "@/components/field/field-handoff-console";
import { FieldWorkspaceCommandCenter } from "@/components/field/workspace_command_center";
import { AuditFieldBootstrap } from "@/components/field/audit-field-bootstrap";

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
      <AuditFieldBootstrap />
      <div className="space-y-5">
        {tenderKey && requirementId ? <FieldHandoffConsole tenderKey={tenderKey} requirementId={requirementId} /> : null}
        <FieldEvidenceMap />
        <FieldWorkspaceCommandCenter />
      </div>
    </PageShell>
  );
}
