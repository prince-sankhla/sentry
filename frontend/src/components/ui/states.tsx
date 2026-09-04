import { AlertTriangle, Database, Loader2, RefreshCcw } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Empty / error / loading / skeleton states.
 * These are deliberately calm and actionable: an unavailable upstream service
 * should read as a recoverable system condition, not as an analytical finding.
 */

function userFacingErrorMessage(message: string): string {
  const normalized = message.trim().toLowerCase();
  if (normalized === "failed to fetch" || normalized.includes("networkerror") || normalized.includes("fetch failed")) {
    return "SENTRY could not retrieve the investigation data. Check the connection and retry. No investigative conclusion was produced.";
  }
  return message;
}

export function EmptyState({
  message,
  title = "No records found",
  icon,
  action,
  suggestions
}: {
  message: string;
  title?: string;
  icon?: ReactNode;
  action?: ReactNode;
  suggestions?: string[];
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-border bg-bg-2/30 px-8 py-16 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl border border-border bg-surface text-muted elevate">
        {icon ?? <Database className="h-6 w-6" aria-hidden="true" />}
      </span>
      <h3 className="mt-6 text-[17px] font-semibold tracking-[-0.014em] text-text">{title}</h3>
      <p className="mt-2 max-w-sm text-[14px] leading-relaxed text-muted">{message}</p>
      {suggestions && suggestions.length > 0 && (
        <ul className="mt-5 space-y-1.5 text-left">
          {suggestions.map((s) => (
            <li key={s} className="flex items-center gap-2 text-[13px] text-faint">
              <span className="h-1 w-1 shrink-0 rounded-full bg-accent" />
              {s}
            </li>
          ))}
        </ul>
      )}
      {action ? <div className="mt-7">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  message,
  title = "Unable to load data",
  action,
  onRetry
}: {
  message: string;
  title?: string;
  action?: ReactNode;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="flex flex-col items-center rounded-2xl border border-danger/25 bg-danger/[0.04] px-8 py-16 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl border border-danger/40 bg-danger/10 text-danger">
        <AlertTriangle className="h-6 w-6" aria-hidden="true" />
      </span>
      <h3 className="mt-6 text-[17px] font-semibold tracking-[-0.014em] text-text">{title}</h3>
      <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-muted">{userFacingErrorMessage(message)}</p>
      <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2 text-sm font-medium text-text transition-colors duration-200 hover:border-border-strong hover:bg-surface-2"
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            Try again
          </button>
        )}
        {action}
      </div>
    </div>
  );
}

export function LoadingState({ message = "Loading intelligence workspace" }: { message?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex min-h-[360px] items-center justify-center rounded-2xl border border-border bg-surface elevate">
      <div className="flex flex-col items-center gap-4 text-[13px] text-muted">
        <Loader2 className="h-5 w-5 animate-spin text-accent" aria-hidden="true" />
        {message}
      </div>
    </div>
  );
}

export function SuccessState({
  message,
  title = "Done",
  icon,
  action
}: {
  message: string;
  title?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-success/25 bg-success/[0.04] px-8 py-16 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl border border-success/40 bg-success/10 text-success">
        {icon ?? <Database className="h-6 w-6" aria-hidden="true" />}
      </span>
      <h3 className="mt-6 text-[17px] font-semibold tracking-[-0.014em] text-text">{title}</h3>
      <p className="mt-2 max-w-sm text-[14px] leading-relaxed text-muted">{message}</p>
      {action ? <div className="mt-7">{action}</div> : null}
    </div>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded-xl ${className}`} />;
}

export function SkeletonText({ lines = 3, className = "" }: { lines?: number; className?: string }) {
  const widths = ["w-full", "w-11/12", "w-4/5", "w-9/12", "w-10/12"];
  return (
    <div className={`space-y-2.5 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`shimmer h-3 rounded-md ${widths[i % widths.length]}`} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 6 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface elevate">
      <div className="border-b border-border bg-bg-2/50 px-5 py-3.5"><div className="shimmer h-3 w-40 rounded-md" /></div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-4">
            <div className="shimmer h-3 flex-1 rounded-md" />
            <div className="shimmer h-3 w-24 rounded-md" />
            <div className="shimmer h-3 w-16 rounded-md" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonCards({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-border bg-surface p-5 elevate">
          <div className="shimmer h-2.5 w-20 rounded-md" />
          <div className="shimmer mt-4 h-7 w-28 rounded-md" />
          <div className="shimmer mt-3 h-2.5 w-24 rounded-md" />
        </div>
      ))}
    </div>
  );
}
