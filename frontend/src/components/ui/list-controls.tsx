"use client";

import { ChevronLeft, ChevronRight, Loader2, Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";

export function ListControls({
  placeholder = "Search…",
  sortOptions,
  total,
  limit,
  offset
}: {
  placeholder?: string;
  sortOptions?: { value: string; label: string }[];
  total: number;
  limit: number;
  offset: number;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [value, setValue] = useState(params.get("q") ?? "");

  function push(next: URLSearchParams) {
    startTransition(() => router.push(`${pathname}?${next.toString()}`));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const next = new URLSearchParams(params.toString());
    if (value.trim()) next.set("q", value.trim());
    else next.delete("q");
    next.set("offset", "0");
    push(next);
  }

  function setSort(sort: string) {
    const next = new URLSearchParams(params.toString());
    next.set("sort", sort);
    next.set("offset", "0");
    push(next);
  }

  function page(dir: -1 | 1) {
    const next = new URLSearchParams(params.toString());
    next.set("offset", String(Math.max(0, offset + dir * limit)));
    push(next);
  }

  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);
  const currentSort = params.get("sort") ?? sortOptions?.[0]?.value ?? "";

  return (
    <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <form onSubmit={submit} className="relative w-full max-w-md">
        {pending ? (
          <Loader2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-accent" />
        ) : (
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        )}
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/60"
        />
      </form>

      <div className="flex items-center gap-2">
        {sortOptions && (
          <select
            value={currentSort}
            onChange={(e) => setSort(e.target.value)}
            className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text outline-none transition focus:border-accent/60"
          >
            {sortOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        )}
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-2 py-1.5">
          <span className="px-1 text-xs tabular text-muted">
            {start}–{end} of {total.toLocaleString()}
          </span>
          <button
            onClick={() => page(-1)}
            disabled={offset === 0 || pending}
            className="grid h-7 w-7 place-items-center rounded-md text-muted transition enabled:hover:bg-surface-2 enabled:hover:text-text disabled:opacity-30"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => page(1)}
            disabled={end >= total || pending}
            className="grid h-7 w-7 place-items-center rounded-md text-muted transition enabled:hover:bg-surface-2 enabled:hover:text-text disabled:opacity-30"
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
