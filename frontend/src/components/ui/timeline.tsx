export type TimelineItem = {
  label: string;
  value: string;
  detail?: string;
};

export function Timeline({
  items,
  onSelect,
  selectedKey
}: {
  items: TimelineItem[];
  onSelect?: (item: TimelineItem) => void;
  selectedKey?: string | null;
}) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <button
          className={`grid w-full grid-cols-[18px_1fr] gap-3 rounded-[4px] border border-transparent p-0 text-left transition hover:border-[#2A2A2A] hover:bg-[#181818] ${selectedKey === `${item.label}-${item.value}` ? "border-[#B59A5B] bg-[#181818]" : ""}`}
          key={`${item.label}-${item.value}`}
          onClick={() => onSelect?.(item)}
          type="button"
        >
          <div className="relative">
            <div className="mt-1 h-2.5 w-2.5 border border-[#B59A5B] bg-[#111111]" />
            <div className="absolute left-[4px] top-4 h-full w-px bg-[#2A2A2A]" />
          </div>
          <div className="py-2 pr-2">
            <div className="text-sm font-semibold text-[#F7F7F7]">{item.label}</div>
            <div className="sentry-mono mt-1 text-xs text-[#A3A3A3]">{item.value}</div>
            {item.detail ? <div className="mt-1 text-xs text-[#A3A3A3]">{item.detail}</div> : null}
          </div>
        </button>
      ))}
    </div>
  );
}
