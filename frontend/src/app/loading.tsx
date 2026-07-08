import { PageShell } from "@/components/ui/page";
import { SkeletonBlock } from "@/components/ui/states";

export default function Loading() {
  return (
    <PageShell>
      <SkeletonBlock className="h-4 w-44" />
      <SkeletonBlock className="mt-3 h-10 w-80 max-w-full" />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock className="h-32 rounded-[16px]" key={index} />
        ))}
      </div>
      <div className="mt-6 grid gap-5 xl:grid-cols-[1.35fr_1fr]">
        <SkeletonBlock className="h-96 rounded-[16px]" />
        <SkeletonBlock className="h-96 rounded-[16px]" />
      </div>
    </PageShell>
  );
}
