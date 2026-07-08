import { PageShell } from "@/components/ui/page";
import { SkeletonBlock } from "@/components/ui/states";

export default function Loading() {
  return (
    <PageShell>
      <SkeletonBlock className="h-4 w-40" />
      <SkeletonBlock className="mt-4 h-10 w-72" />
      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_340px]">
        <SkeletonBlock className="h-[720px] rounded-[16px]" />
        <SkeletonBlock className="h-[720px] rounded-[16px]" />
      </div>
    </PageShell>
  );
}
