import { PageShell } from "@/components/ui/page";
import { SkeletonBlock } from "@/components/ui/states";

export default function Loading() {
  return (
    <PageShell>
      <div className="grid w-full gap-5 xl:grid-cols-[340px_1fr]">
        <aside className="space-y-5">
          <SkeletonBlock className="h-72 rounded-2xl" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            {Array.from({ length: 4 }).map((_, index) => (
              <SkeletonBlock className="h-24 rounded-2xl" key={index} />
            ))}
          </div>
        </aside>
        <div className="space-y-5">
          <SkeletonBlock className="h-36 rounded-2xl" />
          <SkeletonBlock className="h-96 rounded-2xl" />
          <SkeletonBlock className="h-72 rounded-2xl" />
        </div>
      </div>
    </PageShell>
  );
}
