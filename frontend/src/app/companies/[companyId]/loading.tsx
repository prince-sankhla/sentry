import { PageShell } from "@/components/ui/page";
import { SkeletonBlock } from "@/components/ui/states";

export default function Loading() {
  return (
    <PageShell>
      <div className="grid w-full gap-5 xl:grid-cols-[340px_1fr]">
        <aside className="space-y-5">
          <SkeletonBlock className="h-72 rounded-[16px]" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            {Array.from({ length: 4 }).map((_, index) => (
              <SkeletonBlock className="h-24 rounded-[16px]" key={index} />
            ))}
          </div>
        </aside>
        <div className="space-y-5">
          <SkeletonBlock className="h-36 rounded-[16px]" />
          <SkeletonBlock className="h-96 rounded-[16px]" />
          <SkeletonBlock className="h-72 rounded-[16px]" />
        </div>
      </div>
    </PageShell>
  );
}
