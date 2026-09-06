import { PageShell } from "@/components/ui/page";
import { FieldWorkspaceFast } from "@/components/field/workspace_fast";

export const dynamic = "force-dynamic";

export default function FieldPage() {
  return (
    <PageShell>
      <FieldWorkspaceFast />
    </PageShell>
  );
}
