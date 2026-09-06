import { PageShell } from "@/components/ui/page";
import { FieldWorkspace } from "@/components/field/workspace";

export const dynamic = "force-dynamic";

export default function FieldPage() {
  return (
    <PageShell>
      <FieldWorkspace />
    </PageShell>
  );
}
