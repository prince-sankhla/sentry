"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useTransition } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

import type { TenderSort } from "@/lib/api";

type Props = {
  limit: number;
  offset: number;
  total: number;
  query: string;
  sort: TenderSort;
};

const sortOptions: { label: string; value: TenderSort }[] = [
  { label: "Newest", value: "newest" },
  { label: "Published date", value: "published_date" },
  { label: "Estimated value", value: "value" },
  { label: "Title", value: "title" }
];

export function TenderSearchControls({ limit, offset, total, query, sort }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const currentPage = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const hasPrevious = offset > 0;
  const hasNext = offset + limit < total;

  function updateParams(updates: Record<string, string | number | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "") {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    }

    startTransition(() => {
      router.push(`${pathname}?${params.toString()}`);
    });
  }

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const nextQuery = String(formData.get("q") ?? "").trim();
    updateParams({ q: nextQuery || null, offset: 0 });
  }

  return (
    <div className="rounded-[6px] border border-[#2A3441] bg-[#121821] p-4">
      <form className="grid gap-3 md:grid-cols-[1fr_180px_auto]" onSubmit={onSearch}>
        <label className="relative block">
          <span className="sr-only">Search tenders</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA4AF]" aria-hidden="true" />
          <input
            className="h-11 w-full rounded-[4px] border border-[#2A3441] bg-[#0B0F14] pl-9 pr-3 text-sm text-[#E6E8EB] outline-none transition placeholder:text-[#6f7a86] focus:border-[#C58B2A]"
            defaultValue={query}
            name="q"
            placeholder="Search by title or procuring entity"
            type="search"
          />
        </label>

        <label className="block">
          <span className="sr-only">Sort tenders</span>
          <select
            className="h-11 w-full rounded-[4px] border border-[#2A3441] bg-[#0B0F14] px-3 text-sm text-[#E6E8EB] outline-none transition focus:border-[#C58B2A]"
            onChange={(event) => updateParams({ sort: event.target.value, offset: 0 })}
            value={sort}
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <button
          className="h-11 rounded-[4px] border border-[#C58B2A] bg-[#2A2115] px-5 text-sm font-semibold text-[#F3D59A] transition hover:bg-[#332719] disabled:cursor-not-allowed disabled:opacity-45"
          disabled={isPending}
          type="submit"
        >
          Search
        </button>
      </form>

      <div className="mt-4 flex flex-col gap-3 text-sm text-[#9AA4AF] sm:flex-row sm:items-center sm:justify-between">
        <div aria-live="polite">
          {isPending ? "Loading results..." : `Page ${currentPage} of ${pageCount}`}
        </div>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-[4px] border border-[#2A3441] px-3 py-2 font-medium text-[#E6E8EB] transition hover:bg-[#171F2A] disabled:cursor-not-allowed disabled:opacity-45"
            disabled={!hasPrevious || isPending}
            onClick={() => updateParams({ offset: Math.max(0, offset - limit) })}
            type="button"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            Previous
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-[4px] border border-[#2A3441] px-3 py-2 font-medium text-[#E6E8EB] transition hover:bg-[#171F2A] disabled:cursor-not-allowed disabled:opacity-45"
            disabled={!hasNext || isPending}
            onClick={() => updateParams({ offset: offset + limit })}
            type="button"
          >
            Next
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
