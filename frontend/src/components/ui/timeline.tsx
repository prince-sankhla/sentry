import type { ReactNode } from "react";

export type TimelineItem = {
  label: string;
  value: string;
  detail?: string;
  tone?: "accent" | "success" | "warning" | "danger" | "neutral";
  icon?: ReactNode;
};

const DOT_TONES = {
  accent: "border-accent bg-accent/20",
  success: "border-success bg-success/20",
  warning: "border-warning bg-warning/20",
  danger: "border-danger bg-danger/20",
  neutral: "border-border-strong bg-surface-2"
} as const;

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <div className="space-y-1">
      {items.map((item, i) => (
        <div
          className="grid grid-cols-[24px_1fr] gap-3 rounded-[12px] p-2 transition hover:bg-surface-2/50"
          key={`${item.label}-${item.value}-${i}`}
        >
          <div className="relative flex justify-center">
            <div
              className={`z-10 mt-1 grid h-4 w-4 place-items-center rounded-full border ${
                DOT_TONES[item.tone ?? "accent"]
              }`}
            >
              {item.icon ? <span className="text-[10px] text-text">{item.icon}</span> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
            </div>
            {i < items.length - 1 && (
              <div className="absolute left-1/2 top-5 h-[calc(100%+4px)] w-px -translate-x-1/2 bg-border" />
            )}
          </div>
          <div className="pb-1">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 text-sm font-medium text-text">{item.label}</div>
              <div className="shrink-0 text-xs tabular text-muted">{item.value}</div>
            </div>
            {item.detail ? (
              <div className="mt-0.5 truncate text-xs text-faint">{item.detail}</div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}
