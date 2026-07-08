import { AlertTriangle, Database, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  message,
  title = "No records found",
  icon,
  action
}: {
  message: string;
  title?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-[16px] border border-dashed border-border bg-bg-2/40 px-6 py-10 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full border border-border bg-surface text-muted">
        {icon ?? <Database className="h-5 w-5" aria-hidden="true" />}
      </span>
      <h3 className="mt-4 text-sm font-semibold text-text">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted">{message}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  message,
  title = "Unable to load data"
}: {
  message: string;
  title?: string;
}) {
  return (
    <div className="flex flex-col items-center rounded-[16px] border border-danger/30 bg-danger/5 px-6 py-10 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full border border-danger/40 bg-danger/10 text-danger">
        <AlertTriangle className="h-5 w-5" aria-hidden="true" />
      </span>
      <h3 className="mt-4 text-sm font-semibold text-text">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted">{message}</p>
    </div>
  );
}

export function LoadingState({
  message = "Loading intelligence workspace"
}: {
  message?: string;
}) {
  return (
    <div className="flex min-h-[320px] items-center justify-center rounded-[16px] border border-border bg-surface">
      <div className="flex items-center gap-3 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />
        {message}
      </div>
    </div>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded-lg ${className}`} />;
}
