"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { SearchInput, Select } from "@/components/ui/input";

/**
 * Search + sort + pagination rail for list routes.
 *
 * All state lives in the URL — this component only reads `searchParams` and
 * pushes new ones, so results stay linkable and the back button works.
 */
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
    <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <form onSubmit={submit} className="w-full max-w-md">
        <SearchInput
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          pending={pending}
          aria-label={placeholder}
        />
      </form>

      <div className="flex items-center gap-2.5">
        {sortOptions && (
          <Select
            value={currentSort}
            onChange={(e) => setSort(e.target.value)}
            aria-label="Sort results"
            className="min-w-[160px]"
          >
            {sortOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        )}
        <div className="flex items-center gap-1 rounded-xl border border-border bg-bg-2/50 p-1">
          <span className="px-2 text-xs tabular text-muted">
            {start}–{end} of {total.toLocaleString()}
          </span>
          <Button
            variant="ghost"
            size="sm"
            iconOnly
            onClick={() => page(-1)}
            disabled={offset === 0 || pending}
            aria-label="Previous page"
            icon={<ChevronLeft className="h-4 w-4" />}
          />
          <Button
            variant="ghost"
            size="sm"
            iconOnly
            onClick={() => page(1)}
            disabled={end >= total || pending}
            aria-label="Next page"
            icon={<ChevronRight className="h-4 w-4" />}
          />
        </div>
      </div>
    </div>
  );
}
