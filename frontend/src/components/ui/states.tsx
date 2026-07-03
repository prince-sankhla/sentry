import { AlertTriangle, Database, Loader2 } from "lucide-react";

export function EmptyState({ message, title = "No records found" }: { message: string; title?: string }) {
  return (
    <div className="border border-dashed border-[#E8D8B1] bg-[#FCFAF5] p-6 text-center">
      <Database className="mx-auto h-5 w-5 text-[#B88927]" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-[#2F2F2F]">{title}</h3>
      <p className="mt-1 text-sm text-[#6B7280]">{message}</p>
    </div>
  );
}

export function ErrorState({ message, title = "Unable to load data" }: { message: string; title?: string }) {
  return (
    <div className="border border-[#C97A7A] bg-[#FFF7F7] p-6 text-center">
      <AlertTriangle className="mx-auto h-5 w-5 text-[#C97A7A]" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-[#2F2F2F]">{title}</h3>
      <p className="mt-1 text-sm text-[#6B7280]">{message}</p>
    </div>
  );
}

export function LoadingState({ message = "Loading intelligence workspace" }: { message?: string }) {
  return (
    <div className="flex min-h-[320px] items-center justify-center border border-[#E8D8B1] bg-white">
      <div className="flex items-center gap-3 text-sm text-[#6B7280]">
        <Loader2 className="h-4 w-4 animate-spin text-[#B88927]" aria-hidden="true" />
        {message}
      </div>
    </div>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-[#F0E4C8] ${className}`} />;
}
