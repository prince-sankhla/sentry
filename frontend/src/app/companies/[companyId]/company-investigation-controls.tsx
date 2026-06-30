"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useTransition } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

import type { CompanyTenderSort } from "@/lib/api";

type Props = {
  limit: number;
  offset: number;
  query: string;
  sort: CompanyTenderSort;
  total: number;
};

const sortOptions: { label: string; value: CompanyTenderSort }[] = [
  { label: "Latest activity", value: "latest" },
  { label: "Publication date", value: "published_date" },
  { label: "Tender value", value: "value" },
  { label: "Award value", value: "award_value" },
  { label: "Title", value: "title" }
];

export function CompanyInvestigationControls({ limit, offset, query, sort, total }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
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
      <form className="grid gap-3 lg:grid-cols-[1fr_190px_auto]" onSubmit={onSearch}>
        <label className="relative block">
          <span className="sr-only">Search procurement history</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA4AF]" aria-hidden="true" />
          <input
            className="h-11 w-full rounded-[4px] border border-[#2A3441] bg-[#0B0F14] pl-9 pr-3 text-sm text-[#E6E8EB] outline-none transition placeholder:text-[#6f7a86] focus:border-[#C58B2A]"
            defaultValue={query}
            name="q"
            placeholder="Search procurement history"
            type="search"
          />
        </label>
        <select
          className="h-11 rounded-[4px] border border-[#2A3441] bg-[#0B0F14] px-3 text-sm text-[#E6E8EB] outline-none transition focus:border-[#C58B2A]"
          onChange={(event) => updateParams({ sort: event.target.value, offset: 0 })}
          value={sort}
        >
          {sortOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button
          className="h-11 rounded-[4px] border border-[#C58B2A] bg-[#2A2115] px-5 text-sm font-semibold text-[#F3D59A] transition hover:bg-[#332719] disabled:cursor-not-allowed disabled:opacity-45"
          disabled={isPending}
          type="submit"
        >
          Search
        </button>
      </form>

      <div className="mt-4 flex flex-col gap-3 text-sm text-[#9AA4AF] sm:flex-row sm:items-center sm:justify-between">
        <div aria-live="polite">{isPending ? "Loading procurement history..." : `Page ${page} of ${pages}`}</div>
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
