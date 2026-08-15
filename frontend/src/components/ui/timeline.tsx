import type { ReactNode } from "react";

/**
 * Timeline.
 *
 * A single hairline spine with tonal nodes. Tones follow the risk lattice for
 * anything that encodes severity — `accent` is available but should be spent
 * only on the entry the reader is meant to act on.
 */

export type TimelineItem = {
  label: string;
  value: string;
  detail?: string;
  tone?: "accent" | "success" | "warning" | "danger" | "neutral";
  icon?: ReactNode;
};

const DOT_TONES = {
  accent: "border-accent bg-accent/20 text-accent",
  success: "border-success bg-success/20 text-success",
  warning: "border-warning bg-warning/20 text-warning",
  danger: "border-danger bg-danger/20 text-danger",
  neutral: "border-border-strong bg-surface-2 text-muted"
} as const;

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="space-y-1">
      {items.map((item, i) => (
        <li
          className="grid grid-cols-[28px_1fr] gap-4 rounded-xl p-2.5 transition-colors duration-200 hover:bg-surface-2/40"
          key={`${item.label}-${item.value}-${i}`}
        >
          <div className="relative flex justify-center">
            <div
              className={`z-10 mt-1 grid h-5 w-5 place-items-center rounded-full border ${
                DOT_TONES[item.tone ?? "neutral"]
              }`}
            >
              {item.icon ? (
                <span className="text-[10px]">{item.icon}</span>
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
              )}
            </div>
            {i < items.length - 1 && (
              <div
                className="absolute left-1/2 top-6 h-[calc(100%+8px)] w-px -translate-x-1/2 bg-border"
                aria-hidden
              />
            )}
          </div>
          <div className="pb-2">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 text-[14px] font-medium leading-snug text-text">
                {item.label}
              </div>
              <time className="shrink-0 tabular text-xs text-muted">
                {item.value}
              </time>
            </div>
            {item.detail ? (
              <div className="mt-1 text-[13px] leading-relaxed text-faint">
                {item.detail}
              </div>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
