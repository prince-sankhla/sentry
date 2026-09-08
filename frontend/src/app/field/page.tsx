import { PageShell } from "@/components/ui/page";
import { FieldEvidenceMap } from "@/components/field/field_evidence_map";
import { FieldWorkspaceCommandCenter } from "@/components/field/workspace_command_center";
import { AuditFieldBootstrap } from "@/components/field/audit-field-bootstrap";

export const dynamic = "force-dynamic";

export default function FieldPage() {
  return (
    <PageShell>
      <AuditFieldBootstrap />
      <div className="space-y-5">
        <FieldEvidenceMap />
        <FieldWorkspaceCommandCenter />
      </div>
    </PageShell>
  );
}
