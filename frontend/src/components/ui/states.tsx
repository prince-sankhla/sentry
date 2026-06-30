import { AlertTriangle, Database } from "lucide-react";

export function EmptyState({ message, title = "No records found" }: { message: string; title?: string }) {
  return (
    <div className="border border-dashed border-[#2A2A2A] bg-[#111111] p-6 text-center">
      <Database className="mx-auto h-5 w-5 text-[#737373]" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-[#F7F7F7]">{title}</h3>
      <p className="mt-1 text-sm text-[#A3A3A3]">{message}</p>
    </div>
  );
}

export function ErrorState({ message, title = "Unable to load data" }: { message: string; title?: string }) {
  return (
    <div className="border border-[#9A5A5A] bg-[#181818] p-6 text-center">
      <AlertTriangle className="mx-auto h-5 w-5 text-[#9A5A5A]" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-[#F7F7F7]">{title}</h3>
      <p className="mt-1 text-sm text-[#A3A3A3]">{message}</p>
    </div>
  );
}

export function LoadingState({ message = "Loading intelligence workspace" }: { message?: string }) {
  return (
    <div className="min-h-[320px] border border-[#2A2A2A] bg-[#111111] p-6">
      <div className="text-sm font-semibold text-[#F7F7F7]">{message}</div>
      <div className="mt-5 space-y-3">
        <SkeletonBlock className="h-4 w-2/3" />
        <SkeletonBlock className="h-4 w-1/2" />
        <SkeletonBlock className="h-24 w-full" />
      </div>
    </div>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-[#181818] ${className}`} />;
}
