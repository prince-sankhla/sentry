export type TimelineItem = {
  label: string;
  value: string;
  detail?: string;
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div className="grid grid-cols-[18px_1fr] gap-3" key={`${item.label}-${item.value}`}>
          <div className="relative">
            <div className="mt-1 h-2.5 w-2.5 rounded-full border border-[#D97706] bg-white" />
            <div className="absolute left-[4px] top-4 h-full w-px bg-[#E8D8B1]" />
          </div>
          <div>
            <div className="text-sm font-semibold text-[#2F2F2F]">{item.label}</div>
            <div className="mt-1 text-xs text-[#6B7280]">{item.value}</div>
            {item.detail ? <div className="mt-1 text-xs text-[#6B7280]">{item.detail}</div> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
