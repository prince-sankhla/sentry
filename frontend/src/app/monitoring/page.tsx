import { LiveMonitoring } from "@/components/intel/live-monitoring";
import { PageShell } from "@/components/ui/page";

export const dynamic = "force-dynamic";

export default function MonitoringPage() {
  return (
    <PageShell>
      <LiveMonitoring />
    </PageShell>
  );
}
