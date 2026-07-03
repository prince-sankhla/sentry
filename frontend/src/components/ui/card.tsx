import type { ReactNode } from "react";

export function SurfaceCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`overflow-hidden rounded-[24px] border border-[#E8D8B1] bg-white shadow-[0_20px_60px_rgba(87,63,14,0.08)] ${className}`}
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
      <div className="flex items-center justify-between gap-4 border-b border-[#F0E4C8] bg-[#FBF7F0] px-5 py-4">
        <div>
          {eyebrow ? <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#B88927]">{eyebrow}</div> : null}
          <h2 className="text-sm font-semibold text-[#2F2F2F]">{title}</h2>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
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
    neutral: "border-[#E8D8B1]",
    accent: "border-[#D4A74B]",
    success: "border-[#8DA175]",
    warning: "border-[#D18A2B]",
    danger: "border-[#C97A7A]"
  };

  return (
    <SurfaceCard className={`p-5 transition duration-150 hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(87,63,14,0.1)] ${tones[tone]}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7A7F87]">{label}</div>
      <div className="mt-3 break-words text-3xl font-semibold leading-tight tabular-nums text-[#2F2F2F]">{value}</div>
      {meta ? <div className="mt-2 text-xs text-[#6B7280]">{meta}</div> : null}
    </SurfaceCard>
  );
}
