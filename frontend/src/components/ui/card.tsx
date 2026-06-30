import type { ReactNode } from "react";

export function SurfaceCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-[6px] border border-[#2A3441] bg-[#121821] shadow-[0_18px_50px_rgba(0,0,0,0.22)] ${className}`}
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
      <div className="flex items-center justify-between gap-4 border-b border-[#2A3441] bg-[#171F2A]/45 px-4 py-3">
        <div>
          {eyebrow ? <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#C58B2A]">{eyebrow}</div> : null}
          <h2 className="text-sm font-semibold text-[#E6E8EB]">{title}</h2>
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
    neutral: "border-[#2A3441]",
    accent: "border-[#C58B2A]",
    success: "border-[#667A52]",
    warning: "border-[#A56A1F]",
    danger: "border-[#8F3A3A]"
  };

  return (
    <SurfaceCard className={`p-4 transition duration-150 hover:-translate-y-0.5 hover:bg-[#171F2A] ${tones[tone]}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9AA4AF]">{label}</div>
      <div className="mt-3 text-2xl font-semibold tabular-nums text-[#E6E8EB]">{value}</div>
      {meta ? <div className="mt-2 text-xs text-[#9AA4AF]">{meta}</div> : null}
    </SurfaceCard>
  );
}
