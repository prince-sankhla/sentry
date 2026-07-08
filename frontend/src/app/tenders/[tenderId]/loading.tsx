import { PageShell } from "@/components/ui/page";
import { SkeletonBlock } from "@/components/ui/states";

export default function Loading() {
  return (
    <PageShell>
      <SkeletonBlock className="h-5 w-32" />
      <SkeletonBlock className="mt-6 h-9 w-3/4" />
      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_340px]">
        <SkeletonBlock className="h-72 rounded-[16px]" />
        <SkeletonBlock className="h-56 rounded-[16px]" />
      </div>
    </PageShell>
  );
}
