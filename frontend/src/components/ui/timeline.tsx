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
    <div className="space-y-4">
      {items.map((item, i) => (
        <div
          className="grid grid-cols-[18px_1fr] gap-3"
          key={`${item.label}-${item.value}-${i}`}
        >
          <div className="relative flex justify-center">
            <div
              className={`z-10 mt-1 h-2.5 w-2.5 rounded-full border ${
                DOT_TONES[item.tone ?? "accent"]
              }`}
            />
            {i < items.length - 1 && (
              <div className="absolute left-1/2 top-3 h-full w-px -translate-x-1/2 bg-border" />
            )}
          </div>
          <div className="pb-1">
            <div className="text-sm font-medium text-text">{item.label}</div>
            <div className="mt-0.5 text-xs text-muted">{item.value}</div>
            {item.detail ? (
              <div className="mt-0.5 text-xs text-faint">{item.detail}</div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}
