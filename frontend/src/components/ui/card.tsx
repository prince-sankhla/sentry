import type { ReactNode } from "react";

export function SurfaceCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-[4px] border border-[#2A2A2A] bg-[#111111] ${className}`}
    >
      {children}
    </section>
  );
}

export function Section({
  action,
  children,
  eyebrow,
  title
}: {
  action?: ReactNode;
  children: ReactNode;
  eyebrow?: string;
  title: string;
}) {
  return (
    <SurfaceCard>
      <div className="flex items-center justify-between gap-4 border-b border-[#2A2A2A] bg-[#111111] px-4 py-3">
        <div>
          {eyebrow ? <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#737373]">{eyebrow}</div> : null}
          <h2 className="text-sm font-semibold text-[#F7F7F7]">{title}</h2>
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </SurfaceCard>
  );
}

export function StatCard({
  label,
  tone = "neutral",
  value,
  meta
}: {
  label: string;
  tone?: "neutral" | "accent" | "success" | "warning" | "danger";
  value: string;
  meta?: string;
}) {
  const tones = {
    neutral: "border-[#2A2A2A]",
    accent: "border-[#B59A5B]",
    success: "border-[#71816D]",
    warning: "border-[#B59A5B]",
    danger: "border-[#9A5A5A]"
  };

  return (
    <SurfaceCard className={`p-4 transition duration-150 ease-out hover:bg-[#181818] ${tones[tone]}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#737373]">{label}</div>
      <div className="sentry-mono mt-3 text-2xl font-semibold tabular-nums text-[#F7F7F7]">{value}</div>
      {meta ? <div className="mt-2 text-xs text-[#A3A3A3]">{meta}</div> : null}
    </SurfaceCard>
  );
}
