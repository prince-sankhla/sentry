import { PageShell } from "@/components/ui/page";
import { FieldWorkspaceCommandCenter } from "@/components/field/workspace_command_center";

export const dynamic = "force-dynamic";

export default function FieldPage() {
  return (
    <PageShell>
      <FieldWorkspaceCommandCenter />
    </PageShell>
  );
}
