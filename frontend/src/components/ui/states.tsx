import { AlertTriangle, Database, Loader2 } from "lucide-react";

export function EmptyState({ message, title = "No records found" }: { message: string; title?: string }) {
  return (
    <div className="border border-dashed border-[#2A3441] bg-[#121821] p-6 text-center">
      <Database className="mx-auto h-5 w-5 text-[#9AA4AF]" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-[#E6E8EB]">{title}</h3>
      <p className="mt-1 text-sm text-[#9AA4AF]">{message}</p>
    </div>
  );
}

export function ErrorState({ message, title = "Unable to load data" }: { message: string; title?: string }) {
  return (
    <div className="border border-[#8F3A3A] bg-[#171F2A] p-6 text-center">
      <AlertTriangle className="mx-auto h-5 w-5 text-[#8F3A3A]" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-[#E6E8EB]">{title}</h3>
      <p className="mt-1 text-sm text-[#9AA4AF]">{message}</p>
    </div>
  );
}

export function LoadingState({ message = "Loading intelligence workspace" }: { message?: string }) {
  return (
    <div className="flex min-h-[320px] items-center justify-center border border-[#2A3441] bg-[#121821]">
      <div className="flex items-center gap-3 text-sm text-[#9AA4AF]">
        <Loader2 className="h-4 w-4 animate-spin text-[#C58B2A]" aria-hidden="true" />
        {message}
      </div>
    </div>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-[#171F2A] ${className}`} />;
}
